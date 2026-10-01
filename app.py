# -*- coding: utf-8 -*-
"""Простая тестовая BI по клону BMPUBLIC на ADB26AI.

Читает только учёткой BMPUBLIC_BI. Пароль и кошелёк берутся из
.secrets рядом с программой или на уровень выше и в страницы не попадают.

    python app.py
    http://127.0.0.1:8765/
"""
from __future__ import annotations

import contextvars
import html
import json
import os
import re
import threading
import time
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse

import oracledb

HERE = Path(__file__).resolve().parent


def secrets_dir() -> Path:
    override = os.environ.get("BMPUBLIC_SECRETS", "").strip()
    if override:
        return Path(override)
    local = HERE / ".secrets"
    parent = HERE.parent / ".secrets"
    if (local / "users.txt").exists():
        return local
    if (parent / "users.txt").exists():
        return parent
    return local
HOST = "127.0.0.1"
PORT = 8765
PREFIX = os.environ.get("BMPUBLIC_PREFIX", "").rstrip("/")


def pub(path: str) -> str:
    if not path.startswith("/"):
        path = "/" + path
    return PREFIX + path


def strip_prefix(path: str) -> str:
    if PREFIX and (path == PREFIX or path.startswith(PREFIX + "/")):
        path = path[len(PREFIX):] or "/"
    return path.rstrip("/") or "/"


WINDOW_FROM = "2025-01-01"
WINDOW_TO = "2027-01-01"

LANG = contextvars.ContextVar("bi_lang", default="ru")
MONTH_RE = re.compile(r"^20\d{2}-(0[1-9]|1[0-2])$")
MONTHS = {
    "ru": "янв фев мар апр май июн июл авг сен окт ноя дек".split(),
    "ro": "ian feb mar apr mai iun iul aug sep oct noi dec".split(),
    "pt": "jan fev mar abr mai jun jul ago set out nov dez".split(),
}
TIP_CODES = ("O", "P", "M", "T", "F", "L")
STR = {
    "ru": {
        "nav_home": "Обзор",
        "nav_orgs": "Организации",
        "nav_products": "Продукция",
        "nav_articles": "Статьи",
        "nav_docs": "Документы",
        "nav_dict": "Справочник",
        "brand_mark": "тест BI",
        "subtitle": "Клон на ADB26AI, только чтение, схема BMPUBLIC. Снимок посчитан {stamp}.",
        "foot_before": "Источник описания подключения:",
        "foot_after": "Учётка BMPUBLIC_BI, служба adb26ai_medium. Суммы в леях, как в поле SUMA.",
        "loading_title": "Загрузка",
        "loading_h": "Считаю агрегаты",
        "loading_p": "Первый заход читает проводки и журнал движений во Франкфурте. Обычно это меньше минуты.",
        "error_adb": "Не удалось прочитать ADB",
        "retry": "Повторить",
        "no_rows": "Нет строк.",
        "no_page": "Нет страницы",
        "no_page_p": "Такой страницы нет.",
        "error_title": "Ошибка",
        "kpi_univers": "карточек справочника",
        "kpi_docs": "документов",
        "kpi_cm": "проводок",
        "kpi_moves": "движений с датой 2025–2026",
        "kpi_turnover": "оборот проводок, леев",
        "aug_note": "Август 2025 — {money} леев при {n} проводках. На графике оборота ниже этот месяц снят, чтобы были видны остальные.",
        "h_docs_month": "Документы по месяцам",
        "h_moves": "Движения продукции, леев",
        "moves_note": "TXSLD, только строки с датой внутри 2025–2026.",
        "h_turnover": "Оборот проводок без августа 2025",
        "h_orgs": "Организации на дебете",
        "orgs_note": "Карточка типа O в поле DTDEP. Сумма проводки целиком отнесена на эту карточку.",
        "orgs_more": "Все {n} карточек с наибольшим оборотом",
        "h_articles": "Статьи операций",
        "articles_note": "Карточка типа T в субконто дебета. Плюс — поступление, минус — выплата.",
        "articles_more": "Все {n} статей",
        "h_products": "Продукция в журнале движений",
        "products_note": "Топ по модулю суммы в TXSLD за 2025–2026. Количество — как лежит в CANT, единицы у позиций разные.",
        "products_more": "Все {n} позиций",
        "h_accounts": "Счета дебета",
        "h_dict_journals": "Справочник и журналы",
        "journals_note": "Журналы документов, поле TIP:",
        "h_limits": "Что в этой копии неполно",
        "lim_tsld": "Остаток TSLD: {n} строк. Живой остаток в архив BI не кладётся.",
        "lim_txsld": "В TXSLD без даты: {empty}. Вне окна 2025–2026: {junk} (годы вроде 225 и 5202). В отчёты они не входят.",
        "lim_codf": "У всех документов поле CODF равно 0, контрагента в шапке нет. Организация берётся из проводки.",
        "lim_snap": "Снимок дампа 20260930_1952. Обновление заняло {seconds} с.",
        "refresh": "Пересчитать с ADB",
        "th_card": "Карточка",
        "th_postings": "Проводок",
        "th_sum": "Сумма",
        "th_article": "Статья",
        "th_item": "Позиция",
        "th_rows": "Строк",
        "th_qty": "Количество",
        "th_account": "Счёт",
        "th_pieces": "Штук",
        "th_type": "Тип карточки",
        "th_journal": "Журнал",
        "th_docs": "Документов",
        "th_code": "Код",
        "th_name": "Название",
        "th_um": "Ед.",
        "th_arch": "Архив",
        "th_date": "Дата",
        "th_number": "Номер",
        "th_currency": "Валюта",
        "th_doc": "Документ",
        "th_debit": "Дебет",
        "th_credit": "Кредит",
        "th_org": "Организация",
        "th_analytic": "Субконто",
        "orgs_h": "Организации и подразделения",
        "orgs_lead": "Карточки типа O с наибольшим модулем суммы на дебете проводки (DTDEP).",
        "products_h": "Продукция",
        "products_lead": "Журнал TXSLD, дата с 01.01.2025 по 31.12.2026, карточка типа P. Отбор по модулю суммы.",
        "articles_h": "Статьи операций",
        "articles_lead": "Субконто дебета, тип T. «Incasari din vanzari» — поступления, отрицательные суммы — выплаты.",
        "docs_h": "Документы",
        "docs_lead": "Шапка TMDB_DOCS. Контрагент в CODF не заполнен ни у одного документа. Номер — NRMANUAL, у части документов он пустой.",
        "docs_all_months": "все месяцы",
        "docs_all_journals": "все журналы",
        "docs_month": "Месяц",
        "docs_journal": "Журнал",
        "docs_number": "Номер",
        "docs_ph": "часть номера",
        "docs_show": "Показать",
        "docs_shown": "Показаны первые {n} строк.",
        "entries_h": "Проводки",
        "entries_need": "Откройте месяц с обзора, организацию или документ. Без фильтра по 122 тысячам строк не хожу.",
        "entries_lead": "До 80 строк. Организация — аналитика дебета, субконто — карточка DTSC.",
        "card_n": "карточка {n}",
        "doc_n": "документ {n}",
        "dict_h": "Справочник TMS_UNIVERS",
        "dict_type": "Тип",
        "dict_name": "Название",
        "dict_ph": "часть названия",
        "dict_all": "все типы",
        "dict_find": "Найти",
        "dict_pick": "Выберите тип или введите часть названия. В справочнике {total} карточек, целиком его не вывожу.",
        "dict_several": "несколько тысяч",
        "yes": "да",
        "tip_none": "без типа",
        "tip_O": "организации",
        "tip_P": "продукция",
        "tip_M": "материалы",
        "tip_T": "статьи операций",
        "tip_F": "основные средства",
        "tip_L": "производство",
    },
    "ro": {
        "nav_home": "Tablou",
        "nav_orgs": "Organizații",
        "nav_products": "Produse",
        "nav_articles": "Articole",
        "nav_docs": "Documente",
        "nav_dict": "Nomenclator",
        "brand_mark": "test BI",
        "subtitle": "Clonă pe ADB26AI, doar citire, schema BMPUBLIC. Calculat la {stamp}.",
        "foot_before": "Sursa descrierii conexiunii:",
        "foot_after": "Contul BMPUBLIC_BI, serviciul adb26ai_medium. Sumele sunt în lei, ca în câmpul SUMA.",
        "loading_title": "Se încarcă",
        "loading_h": "Calculez agregatele",
        "loading_p": "Prima deschidere citește înregistrările și jurnalul de mișcări de la Frankfurt. De obicei durează sub un minut.",
        "error_adb": "Nu am putut citi ADB",
        "retry": "Reîncearcă",
        "no_rows": "Nu sunt rânduri.",
        "no_page": "Pagină inexistentă",
        "no_page_p": "Această pagină nu există.",
        "error_title": "Eroare",
        "kpi_univers": "fișe în nomenclator",
        "kpi_docs": "documente",
        "kpi_cm": "înregistrări contabile",
        "kpi_moves": "mișcări cu dată 2025–2026",
        "kpi_turnover": "rulaj înregistrări, lei",
        "aug_note": "August 2025 — {money} lei la {n} înregistrări. Pe graficul de rulaj de mai jos luna aceasta este scoasă, ca să se vadă restul.",
        "h_docs_month": "Documente pe luni",
        "h_moves": "Mișcări de produse, lei",
        "moves_note": "TXSLD, doar rândurile cu dată în 2025–2026.",
        "h_turnover": "Rulajul înregistrărilor fără august 2025",
        "h_orgs": "Organizații la debit",
        "orgs_note": "Fișă de tip O în câmpul DTDEP. Suma înregistrării este atribuită integral acestei fișe.",
        "orgs_more": "Toate cele {n} fișe cu cel mai mare rulaj",
        "h_articles": "Articole de operațiuni",
        "articles_note": "Fișă de tip T în analitica de debit. Plus înseamnă încasare, minus înseamnă plată.",
        "articles_more": "Toate cele {n} articole",
        "h_products": "Produse în jurnalul de mișcări",
        "products_note": "Top după modulul sumei în TXSLD pentru 2025–2026. Cantitatea vine din CANT, unitățile diferă.",
        "products_more": "Toate cele {n} poziții",
        "h_accounts": "Conturi de debit",
        "h_dict_journals": "Nomenclator și jurnale",
        "journals_note": "Jurnalele documentelor, câmpul TIP:",
        "h_limits": "Ce nu este complet în această copie",
        "lim_tsld": "Sold TSLD: {n} rânduri. Soldul viu nu intră în arhiva BI.",
        "lim_txsld": "În TXSLD fără dată: {empty}. În afara intervalului 2025–2026: {junk} (ani precum 225 și 5202). Nu intră în rapoarte.",
        "lim_codf": "La toate documentele câmpul CODF este 0, nu există partener în antet. Organizația se ia din înregistrare.",
        "lim_snap": "Instantaneu din dump-ul 20260930_1952. Recalcularea a durat {seconds} s.",
        "refresh": "Recalculează din ADB",
        "th_card": "Fișă",
        "th_postings": "Înregistrări",
        "th_sum": "Sumă",
        "th_article": "Articol",
        "th_item": "Poziție",
        "th_rows": "Rânduri",
        "th_qty": "Cantitate",
        "th_account": "Cont",
        "th_pieces": "Buc.",
        "th_type": "Tip fișă",
        "th_journal": "Jurnal",
        "th_docs": "Documente",
        "th_code": "Cod",
        "th_name": "Denumire",
        "th_um": "U.m.",
        "th_arch": "Arhivă",
        "th_date": "Data",
        "th_number": "Număr",
        "th_currency": "Valuta",
        "th_doc": "Document",
        "th_debit": "Debit",
        "th_credit": "Credit",
        "th_org": "Organizație",
        "th_analytic": "Analitică",
        "orgs_h": "Organizații și subdiviziuni",
        "orgs_lead": "Fișe de tip O cu cel mai mare modul al sumei la debitul înregistrării (DTDEP).",
        "products_h": "Produse",
        "products_lead": "Jurnalul TXSLD, de la 01.01.2025 până la 31.12.2026, fișă de tip P. Ordonate după modulul sumei.",
        "articles_h": "Articole de operațiuni",
        "articles_lead": "Analitica de debit, tip T. «Incasari din vanzari» sunt încasări, sumele negative sunt plăți.",
        "docs_h": "Documente",
        "docs_lead": "Antetul TMDB_DOCS. Partenerul din CODF nu este completat la niciun document. Numărul este NRMANUAL, la o parte din documente este gol.",
        "docs_all_months": "toate lunile",
        "docs_all_journals": "toate jurnalele",
        "docs_month": "Luna",
        "docs_journal": "Jurnal",
        "docs_number": "Număr",
        "docs_ph": "parte din număr",
        "docs_show": "Arată",
        "docs_shown": "Sunt afișate primele {n} rânduri.",
        "entries_h": "Înregistrări",
        "entries_need": "Deschideți o lună din tablou, o organizație sau un document. Fără filtru nu citesc cele 122 de mii de rânduri.",
        "entries_lead": "Cel mult 80 de rânduri. Organizația este analitica de debit, analitica DTSC este fișa analitică.",
        "card_n": "fișa {n}",
        "doc_n": "documentul {n}",
        "dict_h": "Nomenclator TMS_UNIVERS",
        "dict_type": "Tip",
        "dict_name": "Denumire",
        "dict_ph": "parte din denumire",
        "dict_all": "toate tipurile",
        "dict_find": "Caută",
        "dict_pick": "Alegeți tipul sau introduceți o parte din denumire. Nomenclatorul are {total} fișe și nu este afișat integral.",
        "dict_several": "câteva mii",
        "yes": "da",
        "tip_none": "fără tip",
        "tip_O": "organizații",
        "tip_P": "produse",
        "tip_M": "materiale",
        "tip_T": "articole de operațiuni",
        "tip_F": "mijloace fixe",
        "tip_L": "producție",
    },
    "pt": {
        "nav_home": "Painel",
        "nav_orgs": "Organizações",
        "nav_products": "Produtos",
        "nav_articles": "Artigos",
        "nav_docs": "Documentos",
        "nav_dict": "Cadastro",
        "brand_mark": "teste BI",
        "subtitle": "Cópia no ADB26AI, só leitura, schema BMPUBLIC. Calculado em {stamp}.",
        "foot_before": "Fonte da descrição da conexão:",
        "foot_after": "Usuário BMPUBLIC_BI, serviço adb26ai_medium. Os valores estão em lei, como no campo SUMA.",
        "loading_title": "Carregando",
        "loading_h": "Calculando os agregados",
        "loading_p": "A primeira abertura lê os lançamentos e o diário de movimentos em Frankfurt. Em geral leva menos de um minuto.",
        "error_adb": "Não foi possível ler o ADB",
        "retry": "Tentar de novo",
        "no_rows": "Não há linhas.",
        "no_page": "Página inexistente",
        "no_page_p": "Esta página não existe.",
        "error_title": "Erro",
        "kpi_univers": "fichas no cadastro",
        "kpi_docs": "documentos",
        "kpi_cm": "lançamentos contábeis",
        "kpi_moves": "movimentos com data em 2025–2026",
        "kpi_turnover": "movimento dos lançamentos, lei",
        "aug_note": "Agosto de 2025 — {money} lei em {n} lançamentos. No gráfico de movimento abaixo este mês fica de fora, para os outros aparecerem.",
        "h_docs_month": "Documentos por mês",
        "h_moves": "Movimentos de produtos, lei",
        "moves_note": "TXSLD, só as linhas com data em 2025–2026.",
        "h_turnover": "Movimento dos lançamentos sem agosto de 2025",
        "h_orgs": "Organizações no débito",
        "orgs_note": "Ficha de tipo O no campo DTDEP. O valor do lançamento inteiro fica nesta ficha.",
        "orgs_more": "Todas as {n} fichas com maior movimento",
        "h_articles": "Artigos de operação",
        "articles_note": "Ficha de tipo T na analítica de débito. Valor positivo é entrada, valor negativo é pagamento.",
        "articles_more": "Todos os {n} artigos",
        "h_products": "Produtos no diário de movimentos",
        "products_note": "Topo pelo módulo do valor em TXSLD para 2025–2026. A quantidade vem de CANT, as unidades mudam.",
        "products_more": "Todos os {n} itens",
        "h_accounts": "Contas de débito",
        "h_dict_journals": "Cadastro e diários",
        "journals_note": "Diários dos documentos, campo TIP:",
        "h_limits": "O que esta cópia não traz por completo",
        "lim_tsld": "Saldo TSLD: {n} linhas. O saldo vivo não entra no arquivo de BI.",
        "lim_txsld": "Em TXSLD sem data: {empty}. Fora de 2025–2026: {junk} (anos como 225 e 5202). Não entram nos relatórios.",
        "lim_codf": "Em todos os documentos o campo CODF é 0, não há parceiro no cabeçalho. A organização vem do lançamento.",
        "lim_snap": "Instantâneo do dump 20260930_1952. A atualização levou {seconds} s.",
        "refresh": "Recalcular no ADB",
        "th_card": "Ficha",
        "th_postings": "Lançamentos",
        "th_sum": "Valor",
        "th_article": "Artigo",
        "th_item": "Item",
        "th_rows": "Linhas",
        "th_qty": "Quantidade",
        "th_account": "Conta",
        "th_pieces": "Qtd.",
        "th_type": "Tipo da ficha",
        "th_journal": "Diário",
        "th_docs": "Documentos",
        "th_code": "Código",
        "th_name": "Nome",
        "th_um": "Un.",
        "th_arch": "Arquivo",
        "th_date": "Data",
        "th_number": "Número",
        "th_currency": "Moeda",
        "th_doc": "Documento",
        "th_debit": "Débito",
        "th_credit": "Crédito",
        "th_org": "Organização",
        "th_analytic": "Analítica",
        "orgs_h": "Organizações e departamentos",
        "orgs_lead": "Fichas de tipo O com o maior módulo do valor no débito do lançamento (DTDEP).",
        "products_h": "Produtos",
        "products_lead": "Diário TXSLD, de 01.01.2025 a 31.12.2026, ficha de tipo P. Ordenadas pelo módulo do valor.",
        "articles_h": "Artigos de operação",
        "articles_lead": "Analítica de débito, tipo T. «Incasari din vanzari» são entradas, valores negativos são pagamentos.",
        "docs_h": "Documentos",
        "docs_lead": "Cabeçalho TMDB_DOCS. O parceiro em CODF não está preenchido em nenhum documento. O número é NRMANUAL e, numa parte dos documentos, está vazio.",
        "docs_all_months": "todos os meses",
        "docs_all_journals": "todos os diários",
        "docs_month": "Mês",
        "docs_journal": "Diário",
        "docs_number": "Número",
        "docs_ph": "parte do número",
        "docs_show": "Mostrar",
        "docs_shown": "São mostradas as primeiras {n} linhas.",
        "entries_h": "Lançamentos",
        "entries_need": "Abra um mês no painel, uma organização ou um documento. Sem filtro eu não leio as 122 mil linhas.",
        "entries_lead": "Até 80 linhas. A organização é a analítica de débito, a analítica DTSC é a ficha analítica.",
        "card_n": "ficha {n}",
        "doc_n": "documento {n}",
        "dict_h": "Cadastro TMS_UNIVERS",
        "dict_type": "Tipo",
        "dict_name": "Nome",
        "dict_ph": "parte do nome",
        "dict_all": "todos os tipos",
        "dict_find": "Buscar",
        "dict_pick": "Escolha o tipo ou digite parte do nome. O cadastro tem {total} fichas e não é mostrado inteiro.",
        "dict_several": "alguns milhares",
        "yes": "sim",
        "tip_none": "sem tipo",
        "tip_O": "organizações",
        "tip_P": "produtos",
        "tip_M": "materiais",
        "tip_T": "artigos de operação",
        "tip_F": "ativos imobilizados",
        "tip_L": "produção",
    },
}
_lang_keys = [set(STR[code]) for code in ("ru", "ro", "pt")]
if not all(keys == _lang_keys[0] for keys in _lang_keys):
    missing = set().union(*_lang_keys) - set.intersection(*_lang_keys)
    raise RuntimeError("traduceri incomplete: " + ", ".join(sorted(missing)))

STATE = {"status": "loading", "error": "", "model": None, "at": None}
STATE_LOCK = threading.Lock()
POOL = None


def _users() -> dict[str, str]:
    found: dict[str, str] = {}
    path = secrets_dir() / "users.txt"
    if not path.exists():
        raise SystemExit(
            "нет users.txt в .secrets рядом с app.py или на уровень выше. "
            "Пароль в репозиторий не кладётся."
        )
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        name, password = line.split(":", 1)
        found[name.strip().upper()] = password.strip()
    if "BMPUBLIC_BI" not in found:
        raise SystemExit("в users.txt нет строки BMPUBLIC_BI")
    return found


def _wallet_password() -> str:
    agent = secrets_dir() / "agent.md"
    if not agent.exists():
        raise SystemExit(f"нет паспорта {agent}")
    text = agent.read_text(encoding="utf-8", errors="replace")
    match = re.search(r"Wallet password\s*\|\s*`([^`]+)`", text)
    if not match:
        raise SystemExit("в паспорте нет пароля кошелька")
    return match.group(1)


def open_pool() -> None:
    global POOL
    wallet = secrets_dir() / "wallet"
    if not (wallet / "tnsnames.ora").exists():
        raise SystemExit(f"нет кошелька {wallet}")
    POOL = oracledb.create_pool(
        user="BMPUBLIC_BI",
        password=_users()["BMPUBLIC_BI"],
        dsn="adb26ai_medium",
        config_dir=str(wallet),
        wallet_location=str(wallet),
        wallet_password=_wallet_password(),
        min=1,
        max=3,
        increment=1,
    )


def rows(sql: str, binds: dict | None = None) -> list[dict]:
    with POOL.acquire() as con:
        con.call_timeout = 180_000
        with con.cursor() as cur:
            cur.execute(sql, binds or None)
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, rec)) for rec in cur.fetchall()]


def one(sql: str, binds: dict | None = None):
    found = rows(sql, binds)
    return found[0] if found else None


def load_model() -> dict:
    started = time.perf_counter()
    counts = one(
        """
        SELECT
          (SELECT COUNT(*) FROM BMPUBLIC.TMS_UNIVERS) univers,
          (SELECT COUNT(*) FROM BMPUBLIC.TMDB_DOCS) docs,
          (SELECT COUNT(*) FROM BMPUBLIC.TMDB_CM) cm,
          (SELECT COUNT(*) FROM BMPUBLIC.TXSLD) txsld,
          (SELECT COUNT(*) FROM BMPUBLIC.TSLD) tsld
        FROM dual
        """
    )
    univers_tip = rows(
        """
        SELECT NVL(TRIM(TIP), '—') tip, COUNT(*) n
        FROM BMPUBLIC.TMS_UNIVERS
        GROUP BY NVL(TRIM(TIP), '—')
        ORDER BY COUNT(*) DESC
        """
    )
    docs_month = rows(
        """
        SELECT TO_CHAR(DATAMANUAL, 'YYYY-MM') ym, COUNT(*) n
        FROM BMPUBLIC.TMDB_DOCS
        GROUP BY TO_CHAR(DATAMANUAL, 'YYYY-MM')
        ORDER BY ym
        """
    )
    docs_tip = rows(
        """
        SELECT NVL(TRIM(TIP), '—') tip, COUNT(*) n
        FROM BMPUBLIC.TMDB_DOCS
        GROUP BY NVL(TRIM(TIP), '—')
        ORDER BY COUNT(*) DESC
        """
    )
    cm_month = rows(
        """
        SELECT TO_CHAR(DATA, 'YYYY-MM') ym, COUNT(*) n,
               ROUND(SUM(NVL(SUMA, 0)), 2) suma
        FROM BMPUBLIC.TMDB_CM
        GROUP BY TO_CHAR(DATA, 'YYYY-MM')
        ORDER BY ym
        """
    )
    move_month = rows(
        f"""
        SELECT TO_CHAR(DATA, 'YYYY-MM') ym, COUNT(*) n,
               ROUND(SUM(NVL(SUMA, 0)), 2) suma
        FROM BMPUBLIC.TXSLD
        WHERE DATA >= DATE '{WINDOW_FROM}' AND DATA < DATE '{WINDOW_TO}'
        GROUP BY TO_CHAR(DATA, 'YYYY-MM')
        ORDER BY ym
        """
    )
    txsld_split = one(
        f"""
        SELECT
          SUM(CASE WHEN DATA IS NULL THEN 1 ELSE 0 END) empty_date,
          SUM(CASE WHEN DATA >= DATE '{WINDOW_FROM}' AND DATA < DATE '{WINDOW_TO}' THEN 1 ELSE 0 END) in_window,
          SUM(CASE WHEN DATA IS NOT NULL AND (DATA < DATE '{WINDOW_FROM}' OR DATA >= DATE '{WINDOW_TO}') THEN 1 ELSE 0 END) junk
        FROM BMPUBLIC.TXSLD
        """
    )
    orgs = rows(
        """
        SELECT * FROM (
          SELECT u.COD cod, u.DENUMIREA name, COUNT(*) n,
                 ROUND(SUM(NVL(c.SUMA, 0)), 2) suma
          FROM BMPUBLIC.TMDB_CM c
          JOIN BMPUBLIC.TMS_UNIVERS u
            ON u.COD = c.DTDEP AND TRIM(u.TIP) = 'O'
          GROUP BY u.COD, u.DENUMIREA
        )
        ORDER BY ABS(suma) DESC
        FETCH FIRST 40 ROWS ONLY
        """
    )
    products = rows(
        f"""
        SELECT * FROM (
          SELECT u.COD cod, u.DENUMIREA name, COUNT(*) n,
                 ROUND(SUM(NVL(x.SUMA, 0)), 2) suma,
                 ROUND(SUM(NVL(x.CANT, 0)), 3) cant
          FROM BMPUBLIC.TXSLD x
          JOIN BMPUBLIC.TMS_UNIVERS u
            ON u.COD = x.SC AND TRIM(u.TIP) = 'P'
          WHERE x.DATA >= DATE '{WINDOW_FROM}' AND x.DATA < DATE '{WINDOW_TO}'
          GROUP BY u.COD, u.DENUMIREA
        )
        ORDER BY ABS(suma) DESC
        FETCH FIRST 40 ROWS ONLY
        """
    )
    articles = rows(
        """
        SELECT * FROM (
          SELECT u.COD cod, u.DENUMIREA name, COUNT(*) n,
                 ROUND(SUM(NVL(c.SUMA, 0)), 2) suma
          FROM BMPUBLIC.TMDB_CM c
          JOIN BMPUBLIC.TMS_UNIVERS u
            ON u.COD = c.DTSC AND TRIM(u.TIP) = 'T'
          GROUP BY u.COD, u.DENUMIREA
        )
        ORDER BY ABS(suma) DESC
        FETCH FIRST 40 ROWS ONLY
        """
    )
    accounts = rows(
        """
        SELECT * FROM (
          SELECT DT acc, COUNT(*) n, ROUND(SUM(NVL(SUMA, 0)), 2) suma
          FROM BMPUBLIC.TMDB_CM
          WHERE DT IS NOT NULL
          GROUP BY DT
        )
        ORDER BY ABS(suma) DESC
        FETCH FIRST 8 ROWS ONLY
        """
    )
    return {
        "counts": counts,
        "univers_tip": univers_tip,
        "docs_month": docs_month,
        "docs_tip": docs_tip,
        "cm_month": cm_month,
        "move_month": move_month,
        "txsld_split": txsld_split,
        "orgs": orgs,
        "products": products,
        "articles": articles,
        "accounts": accounts,
        "seconds": round(time.perf_counter() - started, 1),
    }


def refresh_async() -> None:
    def work() -> None:
        try:
            model = load_model()
        except Exception as exc:
            message = str(exc).splitlines()[0][:300]
            with STATE_LOCK:
                STATE["status"] = "error"
                STATE["error"] = message
            print("load failed", message, flush=True)
            return
        with STATE_LOCK:
            STATE["status"] = "ready"
            STATE["error"] = ""
            STATE["model"] = model
            STATE["at"] = datetime.now()
        print(f"model ready in {model['seconds']}s", flush=True)

    with STATE_LOCK:
        STATE["status"] = "loading"
        STATE["error"] = ""
    threading.Thread(target=work, daemon=True).start()


def lang() -> str:
    return LANG.get()


def tr(key: str, **kwargs) -> str:
    text = STR[lang()].get(key) or STR["ru"][key]
    return text.format(**kwargs) if kwargs else text


def esc(value) -> str:
    if value is None:
        return ""
    return html.escape(str(value).strip())


def num(value) -> str:
    if value is None:
        return "—"
    text = f"{int(value):,}".replace(",", " ")
    return text


def money(value) -> str:
    if value is None:
        return "—"
    number = float(value)
    sign = "−" if number < 0 else ""
    whole, frac = f"{abs(number):.2f}".split(".")
    groups = []
    while whole:
        groups.append(whole[-3:])
        whole = whole[:-3]
    return sign + " ".join(reversed(groups)) + "," + frac


def month_label(ym: str) -> str:
    year, month = ym.split("-")
    return f"{MONTHS[lang()][int(month) - 1]} {year}"


def tip_label(code: str) -> str:
    if not code or code == "—":
        return tr("tip_none")
    key = f"tip_{code}"
    if key in STR["ru"]:
        return f"{code} · {tr(key)}"
    return code


def bars(items: list[tuple]) -> str:
    if not items:
        return f"<p class='muted'>{esc(tr('no_rows'))}</p>"
    peak = max(abs(float(item[1])) for item in items) or 1
    parts = []
    for item in items:
        label = item[0]
        value = float(item[1])
        href = item[2] if len(item) > 2 else None
        width = 0 if value == 0 else max(2, round(abs(value) / peak * 100))
        shown = esc(label)
        if href:
            shown = f"<a href='{href}'>{shown}</a>"
        parts.append(
            "<div class='bar'>"
            f"<span class='bar-label'>{shown}</span>"
            f"<span class='track'><span class='fill' style='width:{width}%'></span></span>"
            f"<span class='bar-value'>{num(value) if value.is_integer() else money(value)}</span>"
            "</div>"
        )
    return "\n".join(parts)


IVAN_SUMMARY = (
    "Senior Software Engineer with 20+ years modernizing business-critical "
    "Delphi / Object Pascal systems - Unicode and 64-bit migrations with "
    "additional hands-on experience in C++, C# and modern software engineering "
    "practices, BDE to FireDAC data layers, replacement of discontinued "
    "third-party components, and incremental Delphi-to-.NET / Delphi-to-Web "
    "transitions. I work at the difficult end of legacy: codebases that cannot "
    "be rewritten, cannot go down, and have to keep running while they change. "
    "That means reading twenty-year-old code carefully, planning migrations "
    "that ship in stages, and leaving a codebase a maintaining team can "
    "actually own. Technical lead experience across distributed, cross-timezone "
    "teams in Brazil, Italy, Poland and Belgium - setting architecture "
    "direction, reviewing code, and mentoring developers. Fluent in English. "
    "After 20 years in consulting, seeking a permanent, fully remote Senior "
    "Delphi Engineer or Technical Lead role with an employer outside Brazil."
)


def brazil_contact() -> str:
    if lang() != "pt":
        return ""
    return (
        "<section class='card ivan'>"
        "<p class='ivan-kicker'>Para questões no Brasil, fale com</p>"
        "<h2>Ivan Souza</h2>"
        "<p>Senior Software Engineer &amp; Technical Lead | "
        "Delphi / Object Pascal Legacy System Modernization Specialist</p>"
        "<p>Juiz de Fora, Brazil (Open to Remote / International)</p>"
        "<p><a href='tel:+5543991025152'>+55 (43) 99102-5152</a>"
        " · <a href='mailto:ilsouza@gmail.com'>ilsouza@gmail.com</a>"
        " · <a href='https://www.linkedin.com/in/ivanlsouza'>linkedin.com/in/ivanlsouza</a></p>"
        "<h3>Resumo profissional</h3>"
        f"<p>{esc(IVAN_SUMMARY)}</p>"
        "</section>"
    )


def page(title: str, body: str, active: str) -> bytes:
    links = [
        (pub("/"), "nav_home", "home"),
        (pub("/orgs"), "nav_orgs", "orgs"),
        (pub("/products"), "nav_products", "products"),
        (pub("/articles"), "nav_articles", "articles"),
        (pub("/docs"), "nav_docs", "docs"),
        (pub("/dict"), "nav_dict", "dict"),
    ]
    nav = []
    for href, key_name, key in links:
        cls = " class='on'" if key == active else ""
        nav.append(f"<a href='{href}'{cls}>{esc(tr(key_name))}</a>")
    current = lang()
    langs = []
    for code, label in (("ru", "Русский"), ("ro", "Română"), ("pt", "Português")):
        cls = " class='on'" if code == current else ""
        langs.append(f"<a href='{pub('/lang/' + code)}'{cls}>{label}</a>")
    html_lang = {"pt": "pt-BR"}.get(current, current)
    with STATE_LOCK:
        status = STATE["status"]
        when = STATE["at"]
    stamp = ""
    if status == "ready" and when:
        stamp = when.strftime("%d.%m.%Y %H:%M")
    doc = f"""<!DOCTYPE html>
<html lang="{html_lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)} · BMPUBLIC</title>
<style>
:root {{
  --bg: #f3efe6;
  --card: #fffdf8;
  --ink: #1c1915;
  --muted: #6e655b;
  --line: #e3d9cc;
  --green: #1d6b48;
  --green-soft: #e5f2eb;
  --brown: #8a4b22;
}}
* {{ box-sizing: border-box; }}
body {{
  margin: 0; color: var(--ink); background: var(--bg);
  font: 16px/1.45 "Segoe UI", sans-serif;
}}
header {{
  padding: 1.2rem 1.4rem 0.8rem;
  border-bottom: 1px solid var(--line);
  background: #faf7f1;
}}
header .wrap, main {{ max-width: 1080px; margin: 0 auto; }}
main {{ padding: 1.2rem 1.4rem 3rem; }}
.brand {{ font-family: Georgia, serif; font-size: 1.7rem; margin: 0; }}
.brand span {{ color: var(--green); }}
.sub {{ color: var(--muted); margin: 0.2rem 0 0.8rem; }}
nav {{ display: flex; flex-wrap: wrap; align-items: baseline; gap: 0.2rem 0.9rem; }}
nav a {{ color: var(--brown); text-decoration: none; }}
nav a.on {{ color: var(--ink); border-bottom: 2px solid var(--green); }}
.langs {{ margin-left: auto; }}
.langs a {{ margin-left: 0.7rem; }}
.kpis {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 0.7rem; }}
.card {{
  background: var(--card); border: 1px solid var(--line);
  border-radius: 10px; padding: 0.8rem 0.9rem;
}}
.kpi b {{ display: block; font-size: 1.45rem; font-variant-numeric: tabular-nums; }}
.kpi span, .muted {{ color: var(--muted); }}
h2 {{ font-family: Georgia, serif; font-size: 1.25rem; margin: 1.4rem 0 0.4rem; }}
.split {{ display: grid; grid-template-columns: 1fr 1fr; gap: 0.8rem; }}
table {{ width: 100%; border-collapse: collapse; background: var(--card); }}
th, td {{ text-align: left; padding: 0.38rem 0.45rem; border-bottom: 1px solid var(--line); vertical-align: top; }}
th {{ color: var(--muted); font-weight: 600; font-size: 0.86rem; }}
td.num, th.num {{ text-align: right; font-variant-numeric: tabular-nums; white-space: nowrap; }}
.neg {{ color: #8d2d2d; }}
a {{ color: var(--green); }}
.bar {{ display: grid; grid-template-columns: 7.2rem 1fr 7.5rem; gap: 0.45rem; align-items: center; margin: 0.28rem 0; }}
.bar-label, .bar-value {{ font-variant-numeric: tabular-nums; font-size: 0.92rem; }}
.bar-value {{ text-align: right; }}
.track {{ background: #efe8dc; height: 0.7rem; border-radius: 99px; }}
.fill {{ display: block; height: 100%; background: var(--green); border-radius: 99px; }}
.note {{ background: var(--green-soft); border-radius: 10px; padding: 0.7rem 0.9rem; }}
.ivan {{ margin: 0 0 1rem; }}
.ivan h2 {{ margin: 0.1rem 0 0.35rem; }}
.ivan h3 {{ font-size: 1rem; margin: 0.85rem 0 0.3rem; }}
.ivan-kicker {{ color: var(--brown); margin: 0; }}
.ivan p {{ margin: 0.28rem 0; }}
form {{ display: flex; flex-wrap: wrap; gap: 0.5rem; align-items: end; margin: 0.6rem 0 1rem; }}
label {{ display: flex; flex-direction: column; font-size: 0.85rem; color: var(--muted); }}
input, select, button {{
  font: inherit; color: var(--ink); background: white;
  border: 1px solid var(--line); border-radius: 8px; padding: 0.35rem 0.5rem;
}}
button {{ background: var(--green); color: white; border-color: var(--green); cursor: pointer; }}
footer {{ color: var(--muted); font-size: 0.88rem; margin-top: 1.6rem; }}
@media (max-width: 760px) {{
  .split {{ grid-template-columns: 1fr; }}
  .bar {{ grid-template-columns: 5.4rem 1fr 5.6rem; }}
}}
</style>
</head>
<body>
<header><div class="wrap">
<p class="brand">BMPUBLIC <span>{esc(tr("brand_mark"))}</span></p>
<p class="sub">{esc(tr("subtitle", stamp=stamp or "…"))}</p>
<nav><span class="links">{''.join(nav)}</span><span class="langs">{''.join(langs)}</span></nav>
</div></header>
<main>
{brazil_contact()}
{body}
<footer>
{esc(tr("foot_before"))} <a href="http://130.61.108.5/bi/">130.61.108.5/bi</a>.
{esc(tr("foot_after"))}
</footer>
</main>
</body>
</html>"""
    return doc.encode("utf-8")


def waiting(status: str, error: str) -> bytes:
    if status == "error":
        body = (
            f"<h2>{esc(tr('error_adb'))}</h2><p>{esc(error)}</p>"
            f"<p><a href='{pub('/refresh')}'>{esc(tr('retry'))}</a></p>"
        )
    else:
        body = (
            "<meta http-equiv=\"refresh\" content=\"3\">"
            f"<h2>{esc(tr('loading_h'))}</h2><p>{esc(tr('loading_p'))}</p>"
        )
    return page(tr("loading_title"), body, "home")


def model_or_wait():
    with STATE_LOCK:
        status = STATE["status"]
        error = STATE["error"]
        model = STATE["model"]
    if status != "ready" or model is None:
        return None, waiting(status, error)
    return model, None


def signed(value) -> str:
    text = money(value)
    if value is not None and float(value) < 0:
        return f"<span class='neg'>{text}</span>"
    return text


def table(headers: list[tuple[str, str]], records: list[list[str]]) -> str:
    head = "".join(
        f"<th class='{kind}'>{esc(label)}</th>" for label, kind in headers
    )
    body = []
    for rec in records:
        cells = []
        for (label, kind), cell in zip(headers, rec):
            cells.append(f"<td class='{kind}'>{cell}</td>")
        body.append("<tr>" + "".join(cells) + "</tr>")
    if not body:
        return f"<p class='muted'>{esc(tr('no_rows'))}</p>"
    return f"<table><thead><tr>{head}</tr></thead><tbody>{''.join(body)}</tbody></table>"


def home() -> bytes:
    model, hold = model_or_wait()
    if hold:
        return hold
    counts = model["counts"]
    split = model["txsld_split"]
    cm_total = sum(float(r["SUMA"] or 0) for r in model["cm_month"])
    aug = next((r for r in model["cm_month"] if r["YM"] == "2025-08"), None)
    rest = [r for r in model["cm_month"] if r["YM"] != "2025-08"]
    kpis = f"""
    <section class="kpis">
      <div class="card kpi"><b>{num(counts['UNIVERS'])}</b><span>{esc(tr('kpi_univers'))}</span></div>
      <div class="card kpi"><b>{num(counts['DOCS'])}</b><span>{esc(tr('kpi_docs'))}</span></div>
      <div class="card kpi"><b>{num(counts['CM'])}</b><span>{esc(tr('kpi_cm'))}</span></div>
      <div class="card kpi"><b>{num(split['IN_WINDOW'])}</b><span>{esc(tr('kpi_moves'))}</span></div>
      <div class="card kpi"><b>{money(cm_total)}</b><span>{esc(tr('kpi_turnover'))}</span></div>
    </section>
    """
    aug_note = ""
    if aug:
        aug_note = (
            "<p class='note'>"
            + esc(tr("aug_note", money=money(aug["SUMA"]), n=num(aug["N"])))
            + "</p>"
        )
    docs_chart = bars(
        [
            (month_label(r["YM"]), float(r["N"]), pub("/docs?month=" + r["YM"]))
            for r in model["docs_month"]
        ]
    )
    move_chart = bars(
        [(month_label(r["YM"]), float(r["SUMA"] or 0)) for r in model["move_month"]]
    )
    turnover = bars(
        [(month_label(r["YM"]), float(r["SUMA"] or 0)) for r in rest]
    )
    org_rows = [
        [
            f"<a href='{pub('/entries?org=' + str(int(r['COD'])))}'>{esc(r['NAME'])}</a>",
            num(r["N"]),
            signed(r["SUMA"]),
        ]
        for r in model["orgs"][:8]
    ]
    product_rows = [
        [esc(r["NAME"]), num(r["N"]), money(r["CANT"]), signed(r["SUMA"])]
        for r in model["products"][:8]
    ]
    article_rows = [
        [esc(r["NAME"]), num(r["N"]), signed(r["SUMA"])] for r in model["articles"][:8]
    ]
    account_rows = [
        [esc(r["ACC"]), num(r["N"]), signed(r["SUMA"])] for r in model["accounts"]
    ]
    tip_rows = [
        [esc(tip_label(r["TIP"])), num(r["N"])] for r in model["univers_tip"]
    ]
    doc_tip_rows = [
        [esc(r["TIP"]), num(r["N"])] for r in model["docs_tip"]
    ]
    body = f"""
    {kpis}
    {aug_note}
    <div class="split">
      <section class="card"><h2>{esc(tr('h_docs_month'))}</h2>{docs_chart}</section>
      <section class="card"><h2>{esc(tr('h_moves'))}</h2>
        <p class="muted">{esc(tr('moves_note'))}</p>
        {move_chart}
      </section>
    </div>
    <section class="card"><h2>{esc(tr('h_turnover'))}</h2>{turnover}</section>
    <div class="split">
      <section>
        <h2>{esc(tr('h_orgs'))}</h2>
        <p class="muted">{esc(tr('orgs_note'))}</p>
        {table([(tr("th_card"), ""), (tr("th_postings"), "num"), (tr("th_sum"), "num")], org_rows)}
        <p><a href="{pub('/orgs')}">{esc(tr("orgs_more", n=len(model["orgs"])))}</a></p>
      </section>
      <section>
        <h2>{esc(tr('h_articles'))}</h2>
        <p class="muted">{esc(tr('articles_note'))}</p>
        {table([(tr("th_article"), ""), (tr("th_postings"), "num"), (tr("th_sum"), "num")], article_rows)}
        <p><a href="{pub('/articles')}">{esc(tr("articles_more", n=len(model["articles"])))}</a></p>
      </section>
    </div>
    <h2>{esc(tr('h_products'))}</h2>
    <p class="muted">{esc(tr('products_note'))}</p>
    {table([(tr("th_item"), ""), (tr("th_rows"), "num"), (tr("th_qty"), "num"), (tr("th_sum"), "num")], product_rows)}
    <p><a href="{pub('/products')}">{esc(tr("products_more", n=len(model["products"])))}</a></p>
    <div class="split">
      <section>
        <h2>{esc(tr('h_accounts'))}</h2>
        {table([(tr("th_account"), ""), (tr("th_postings"), "num"), (tr("th_sum"), "num")], account_rows)}
      </section>
      <section>
        <h2>{esc(tr('h_dict_journals'))}</h2>
        {table([(tr("th_type"), ""), (tr("th_pieces"), "num")], tip_rows)}
        <p class="muted">{esc(tr('journals_note'))}</p>
        {table([(tr("th_journal"), ""), (tr("th_docs"), "num")], doc_tip_rows)}
      </section>
    </div>
    <h2>{esc(tr('h_limits'))}</h2>
    <ul>
      <li>{esc(tr('lim_tsld', n=num(counts['TSLD'])))}</li>
      <li>{esc(tr('lim_txsld', empty=num(split['EMPTY_DATE']), junk=num(split['JUNK'])))}</li>
      <li>{esc(tr('lim_codf'))}</li>
      <li>{esc(tr('lim_snap', seconds=model['seconds']))}</li>
    </ul>
    <p><a href="{pub('/refresh')}">{esc(tr('refresh'))}</a></p>
    """
    return page(tr("nav_home"), body, "home")


def orgs_page() -> bytes:
    model, hold = model_or_wait()
    if hold:
        return hold
    records = [
        [
            f"<a href='{pub('/entries?org=' + str(int(r['COD'])))}'>{esc(r['NAME'])}</a>",
            esc(r["COD"]),
            num(r["N"]),
            signed(r["SUMA"]),
        ]
        for r in model["orgs"]
    ]
    body = (
        f"<h2>{esc(tr('orgs_h'))}</h2>"
        f"<p class='muted'>{esc(tr('orgs_lead'))}</p>"
        + table(
            [
                (tr("th_card"), ""),
                (tr("th_code"), "num"),
                (tr("th_postings"), "num"),
                (tr("th_sum"), "num"),
            ],
            records,
        )
    )
    return page(tr("nav_orgs"), body, "orgs")


def products_page() -> bytes:
    model, hold = model_or_wait()
    if hold:
        return hold
    records = [
        [esc(r["NAME"]), esc(r["COD"]), num(r["N"]), money(r["CANT"]), signed(r["SUMA"])]
        for r in model["products"]
    ]
    body = (
        f"<h2>{esc(tr('products_h'))}</h2>"
        f"<p class='muted'>{esc(tr('products_lead'))}</p>"
        + table(
            [
                (tr("th_item"), ""),
                (tr("th_code"), "num"),
                (tr("th_rows"), "num"),
                (tr("th_qty"), "num"),
                (tr("th_sum"), "num"),
            ],
            records,
        )
    )
    return page(tr("nav_products"), body, "products")


def articles_page() -> bytes:
    model, hold = model_or_wait()
    if hold:
        return hold
    records = [
        [esc(r["NAME"]), esc(r["COD"]), num(r["N"]), signed(r["SUMA"])]
        for r in model["articles"]
    ]
    body = (
        f"<h2>{esc(tr('articles_h'))}</h2>"
        f"<p class='muted'>{esc(tr('articles_lead'))}</p>"
        + table(
            [
                (tr("th_article"), ""),
                (tr("th_code"), "num"),
                (tr("th_postings"), "num"),
                (tr("th_sum"), "num"),
            ],
            records,
        )
    )
    return page(tr("nav_articles"), body, "articles")


def docs_page(query: dict) -> bytes:
    model, hold = model_or_wait()
    if hold:
        return hold
    month = (query.get("month") or [""])[0]
    tip = (query.get("tip") or [""])[0].strip()
    q = (query.get("q") or [""])[0].strip()[:40]
    if month and not MONTH_RE.match(month):
        month = ""
    if tip and not re.fullmatch(r"[A-Za-z#]", tip):
        tip = ""
    where = []
    binds = {}
    if month:
        where.append("TO_CHAR(d.DATAMANUAL, 'YYYY-MM') = :ym")
        binds["ym"] = month
    if tip:
        where.append("TRIM(d.TIP) = :tip")
        binds["tip"] = tip.upper()
    if q:
        where.append("UPPER(d.NRMANUAL) LIKE :q")
        binds["q"] = f"%{q.upper()}%"
    clause = (" WHERE " + " AND ".join(where)) if where else ""
    found = rows(
        f"""
        SELECT d.COD cod, TRIM(d.TIP) tip, d.DATAMANUAL data,
               TRIM(d.NRMANUAL) nr, TRIM(d.VALUTA) valuta
        FROM BMPUBLIC.TMDB_DOCS d
        {clause}
        ORDER BY d.DATAMANUAL DESC, d.COD DESC
        FETCH FIRST 80 ROWS ONLY
        """,
        binds,
    )
    month_options = [f"<option value=''>{esc(tr('docs_all_months'))}</option>"]
    for rec in model["docs_month"]:
        selected = " selected" if rec["YM"] == month else ""
        month_options.append(
            f"<option value='{esc(rec['YM'])}'{selected}>{esc(month_label(rec['YM']))}</option>"
        )
    tip_options = [f"<option value=''>{esc(tr('docs_all_journals'))}</option>"]
    for rec in model["docs_tip"]:
        selected = " selected" if rec["TIP"] == tip.upper() else ""
        tip_options.append(
            f"<option value='{esc(rec['TIP'])}'{selected}>{esc(rec['TIP'])}</option>"
        )
    records = []
    for rec in found:
        when = rec["DATA"].strftime("%d.%m.%Y") if rec["DATA"] else "—"
        records.append(
            [
                when,
                f"<a href='{pub('/entries?doc=' + str(int(rec['COD'])))}'>{esc(rec['COD'])}</a>",
                esc(rec["TIP"] or "—"),
                esc(rec["NR"] or "—"),
                esc(rec["VALUTA"] or "—"),
            ]
        )
    body = f"""
    <h2>{esc(tr('docs_h'))}</h2>
    <p class="muted">{esc(tr('docs_lead'))}</p>
    <form method="get" action="{pub('/docs')}">
      <label>{esc(tr('docs_month'))}<select name="month">{''.join(month_options)}</select></label>
      <label>{esc(tr('docs_journal'))}<select name="tip">{''.join(tip_options)}</select></label>
      <label>{esc(tr('docs_number'))}<input name="q" value="{esc(q)}" placeholder="{esc(tr('docs_ph'))}"></label>
      <button type="submit">{esc(tr('docs_show'))}</button>
    </form>
    """ + table(
        [
            (tr("th_date"), ""),
            (tr("th_code"), "num"),
            (tr("th_journal"), ""),
            (tr("th_number"), ""),
            (tr("th_currency"), ""),
        ],
        records,
    )
    body += f"<p class='muted'>{esc(tr('docs_shown', n=len(found)))}</p>"
    return page(tr("nav_docs"), body, "docs")


def entries_page(query: dict) -> bytes:
    month = (query.get("month") or [""])[0]
    org = (query.get("org") or [""])[0]
    doc = (query.get("doc") or [""])[0]
    if month and not MONTH_RE.match(month):
        month = ""
    org_id = int(org) if org.isdigit() else None
    doc_id = int(doc) if doc.isdigit() else None
    if not month and org_id is None and doc_id is None:
        body = (
            f"<h2>{esc(tr('entries_h'))}</h2><p>{esc(tr('entries_need'))}</p>"
        )
        return page(tr("entries_h"), body, "home")
    where = []
    binds = {}
    if month:
        where.append("TO_CHAR(c.DATA, 'YYYY-MM') = :ym")
        binds["ym"] = month
    if org_id is not None:
        where.append("(c.DTDEP = :org OR c.CTDEP = :org)")
        binds["org"] = org_id
    if doc_id is not None:
        where.append("c.NRDOC = :doc")
        binds["doc"] = doc_id
    found = rows(
        f"""
        SELECT c.DATA data, c.NRDOC nrdoc, c.DT dt, c.CT ct, c.SUMA suma,
               TRIM(c.VALUTADT) valuta, dep.DENUMIREA dep, sc.DENUMIREA sc
        FROM BMPUBLIC.TMDB_CM c
        LEFT JOIN BMPUBLIC.TMS_UNIVERS dep ON dep.COD = c.DTDEP
        LEFT JOIN BMPUBLIC.TMS_UNIVERS sc ON sc.COD = c.DTSC
        WHERE {' AND '.join(where)}
        ORDER BY c.DATA DESC, c.NRDOC DESC
        FETCH FIRST 80 ROWS ONLY
        """,
        binds,
    )
    title_bits = []
    if month:
        title_bits.append(month_label(month))
    if org_id is not None:
        title_bits.append(tr("card_n", n=org_id))
    if doc_id is not None:
        title_bits.append(tr("doc_n", n=doc_id))
    records = []
    for rec in found:
        when = rec["DATA"].strftime("%d.%m.%Y") if rec["DATA"] else "—"
        records.append(
            [
                when,
                f"<a href='{pub('/entries?doc=' + str(int(rec['NRDOC'])))}'>{esc(rec['NRDOC'])}</a>",
                esc(rec["DT"] or "—"),
                esc(rec["CT"] or "—"),
                signed(rec["SUMA"]),
                esc(rec["VALUTA"] or "—"),
                esc(rec["DEP"] or "—"),
                esc(rec["SC"] or "—"),
            ]
        )
    body = f"""
    <h2>{esc(tr('entries_h'))} · {esc(', '.join(title_bits))}</h2>
    <p class="muted">{esc(tr('entries_lead'))}</p>
    """ + table(
        [
            (tr("th_date"), ""),
            (tr("th_doc"), "num"),
            (tr("th_debit"), "num"),
            (tr("th_credit"), "num"),
            (tr("th_sum"), "num"),
            (tr("th_currency"), ""),
            (tr("th_org"), ""),
            (tr("th_analytic"), ""),
        ],
        records,
    )
    return page(tr("entries_h"), body, "home")


def dict_page(query: dict) -> bytes:
    tip = (query.get("tip") or [""])[0].strip().upper()
    q = (query.get("q") or [""])[0].strip()[:60]
    if tip and tip not in TIP_CODES:
        tip = ""
    options = [f"<option value=''>{esc(tr('dict_all'))}</option>"]
    for code in TIP_CODES:
        selected = " selected" if code == tip else ""
        options.append(
            f"<option value='{code}'{selected}>{code} · {esc(tr('tip_' + code))}</option>"
        )
    body = f"""
    <h2>{esc(tr('dict_h'))}</h2>
    <form method="get" action="{pub('/dict')}">
      <label>{esc(tr('dict_type'))}<select name="tip">{''.join(options)}</select></label>
      <label>{esc(tr('dict_name'))}<input name="q" value="{esc(q)}" placeholder="{esc(tr('dict_ph'))}"></label>
      <button type="submit">{esc(tr('dict_find'))}</button>
    </form>
    """
    if not tip and not q:
        with STATE_LOCK:
            ready = STATE["model"]
        total = num(ready["counts"]["UNIVERS"]) if ready else tr("dict_several")
        body += f"<p class='muted'>{esc(tr('dict_pick', total=total))}</p>"
        return page(tr("nav_dict"), body, "dict")
    where = []
    binds = {}
    if tip:
        where.append("TRIM(TIP) = :tip")
        binds["tip"] = tip
    if q:
        where.append("UPPER(DENUMIREA) LIKE :q")
        binds["q"] = f"%{q.upper()}%"
    found = rows(
        f"""
        SELECT COD cod, TRIM(TIP) tip, DENUMIREA name, TRIM(UM) um, TRIM(ISARHIV) archived
        FROM BMPUBLIC.TMS_UNIVERS
        WHERE {' AND '.join(where)}
        ORDER BY DENUMIREA
        FETCH FIRST 80 ROWS ONLY
        """,
        binds,
    )
    records = [
        [
            esc(r["COD"]),
            esc(tip_label(r["TIP"] or "—")),
            esc(r["NAME"]),
            esc(r["UM"] or "—"),
            tr("yes") if (r["ARCHIVED"] or "").upper() in {"1", "Y", "D"} else "—",
        ]
        for r in found
    ]
    body += table(
        [
            (tr("th_code"), "num"),
            (tr("th_type"), ""),
            (tr("th_name"), ""),
            (tr("th_um"), ""),
            (tr("th_arch"), ""),
        ],
        records,
    )
    body += f"<p class='muted'>{esc(tr('docs_shown', n=len(found)))}</p>"
    return page(tr("nav_dict"), body, "dict")


def chosen_lang(header: str | None, query: dict) -> str:
    raw = (query.get("lang") or [""])[0].lower()
    if raw in STR:
        return raw
    for part in (header or "").split(";"):
        if "=" not in part:
            continue
        name, value = part.strip().split("=", 1)
        if name == "bi_lang" and value in STR:
            return value
    return "ru"


def safe_back(referer: str | None) -> str:
    if not referer:
        return pub("/")
    parsed = urlparse(referer)
    inner = strip_prefix(parsed.path or "/")
    if inner.startswith("/lang/"):
        return pub("/")
    kept = []
    for key, values in parse_qs(parsed.query).items():
        if key == "lang":
            continue
        for value in values:
            kept.append((key, value))
    query = urlencode(kept)
    return pub(inner) + (("?" + query) if query else "")


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = strip_prefix(parsed.path)
        query = parse_qs(parsed.query)
        cookie_path = PREFIX or "/"
        if path.startswith("/lang/"):
            chosen = path.rsplit("/", 1)[-1]
            if chosen not in STR:
                body = page(tr("no_page"), f"<p>{esc(tr('no_page_p'))}</p>", "home")
                self._send(404, body, "text/html; charset=utf-8")
                return
            self.send_response(302)
            self.send_header("Location", safe_back(self.headers.get("Referer")))
            self.send_header(
                "Set-Cookie",
                f"bi_lang={chosen}; Path={cookie_path}; Max-Age=31536000; SameSite=Lax",
            )
            self.end_headers()
            return
        if path == "/health":
            with STATE_LOCK:
                payload = {"status": STATE["status"], "error": STATE["error"]}
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self._send(200, body, "application/json; charset=utf-8")
            return
        if path == "/refresh":
            refresh_async()
            self.send_response(302)
            self.send_header("Location", pub("/"))
            self.end_headers()
            return
        LANG.set(chosen_lang(self.headers.get("Cookie"), query))
        asked = (query.get("lang") or [""])[0].lower()
        self._lang_to_set = asked if asked in STR else None
        routes = {
            "/": home,
            "/orgs": orgs_page,
            "/products": products_page,
            "/articles": articles_page,
        }
        try:
            if path in routes:
                body = routes[path]()
            elif path == "/docs":
                body = docs_page(query)
            elif path == "/entries":
                body = entries_page(query)
            elif path == "/dict":
                body = dict_page(query)
            else:
                body = page(tr("no_page"), f"<p>{esc(tr('no_page_p'))}</p>", "home")
                self._send(404, body, "text/html; charset=utf-8")
                return
        except Exception as exc:
            message = str(exc).splitlines()[0][:300]
            body = page(tr("error_title"), f"<p>{esc(message)}</p>", "home")
            self._send(500, body, "text/html; charset=utf-8")
            return
        self._send(200, body, "text/html; charset=utf-8")

    def _send(self, code: int, body: bytes, content_type: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        sticky = getattr(self, "_lang_to_set", None)
        if sticky:
            self.send_header(
                "Set-Cookie",
                f"bi_lang={sticky}; Path={PREFIX or '/'}; Max-Age=31536000; SameSite=Lax",
            )
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt: str, *args) -> None:
        print("%s %s" % (self.address_string(), fmt % args), flush=True)


def main() -> None:
    import sys

    open_pool()
    if "--check" in sys.argv:
        model = load_model()
        print("univers", model["counts"]["UNIVERS"])
        print("docs", model["counts"]["DOCS"])
        print("cm", model["counts"]["CM"])
        print("txsld_window", model["txsld_split"]["IN_WINDOW"])
        print("orgs", len(model["orgs"]), (model["orgs"][0]["NAME"] if model["orgs"] else "")[:40])
        print("products", len(model["products"]))
        print("articles", len(model["articles"]), (model["articles"][0]["NAME"] if model["articles"] else "")[:40])
        print("seconds", model["seconds"])
        return
    refresh_async()
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"http://{HOST}:{PORT}{PREFIX or '/'}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
