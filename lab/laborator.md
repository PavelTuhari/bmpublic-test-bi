# Лабораторная работа. BMPUBLIC на Autonomous Database как источник для любого BI

Снимок данных: `20260930_1952`. Пароль и кошелёк в этот текст не входят: их выдаёт преподаватель отдельно. Пример готового отчёта: http://130.61.108.5/test-bi/ . Описание подключения: http://130.61.108.5/bi/ .

Языки: [русский](#ru), [румынский](#ro), [английский](#en), [португальский (Бразилия)](#pt-br).

---

<a id="ru"></a>

## Русский

### 1. Цель

Научиться подключать внешний BI к схеме `BMPUBLIC` на Oracle Autonomous AI Database и читать из неё отчёт, не изменяя данные. После работы студент объясняет, почему для этого заведена отдельная учётка только на чтение, и знает, какая таблица или представление за что отвечает.

Время: 2–3 академических часа.

### 2. Что уже сделано с базой

Исходная база — Oracle 11.2, схема `BMPUBLIC` на сервере `cloudbd`. Она перенесена на уже существующую Autonomous AI Database `ADB26AI` во Франкфурте. Кодировка облачной базы — `AL32UTF8`. Это копия для отчётов, а не вторая рабочая бухгалтерия.

На момент снимка читателю видны **951 таблица** и **782 представления** схемы `BMPUBLIC`, все в состоянии `VALID`. Рядом существует схема окружения `UN4PUBLIC`. Чужая схема `CRM_APP` при переносе не менялась. Черновики `ZTEM*`, `ZTMP*`, `ZTEMP*` в копию не входили.

Для внешнего доступа заведена учётка `BMPUBLIC_BI`. Ей выданы `CREATE SESSION` и `SELECT` на таблицы и представления `BMPUBLIC`. Прав `ANY`, права записи и права администратора у неё нет. Триггер входа ставит `NLS_DATE_FORMAT = DD.MM.YYYY` и `NLS_LENGTH_SEMANTICS = CHAR`.

Поверх этой учётки сделаны две вещи:

* страница подключения http://130.61.108.5/bi/ — как подключить DBeaver, Power BI, Tableau или Python;
* тестовая BI http://130.61.108.5/test-bi/ — один готовый отчёт на русском, румынском и португальском (Бразилия). Любой другой BI читает ту же базу тем же способом.

### 3. Отдельный пользователь только на чтение

Отчёт подключается учёткой `BMPUBLIC_BI`.

Так и нужно делать в дальнейшей работе. Учётка отчёта умеет открыть сессию и читать выданные объекты. Она не вставляет, не обновляет и не удаляет строки и не меняет структуру. Ошибка в запросе или в настройке BI не портит проводки.

Учётка `ADMIN` для отчёта не используется. У администратора есть объекты других схем, в том числе `CRM_APP`. Отчёт, открытый администратором, показывает чужие данные и может их изменить. Пароль администратора и пароль кошелька на сайт не выкладываются. Кошелёк студент хранит у себя и никуда не отправляет.

Проверка, что учётка именно читающая: любой `UPDATE` или `DELETE` по `BMPUBLIC` должен завершиться ошибкой нехватки прав. Это ожидаемый результат, а не поломка.

### 4. Как любой BI берёт эту базу источником

База принимает соединение взаимным TLS.

| Параметр | Значение |
| --- | --- |
| Хост | `adb.eu-frankfurt-1.oraclecloud.com` |
| Порт | `1522` |
| Протокол | `TCPS` |
| Служба | `g37d999c93838e3_adb26ai_medium.adb.oraclecloud.com` |
| Псевдоним в кошельке | `adb26ai_medium` |
| Схема | `BMPUBLIC` |
| Пользователь | `BMPUBLIC_BI` |

Порядок один и тот же для DBeaver, Power BI, Tableau, Excel и Python.

1. Получить у преподавателя архив кошелька, пароль кошелька и пароль `BMPUBLIC_BI`.
2. Распаковать кошелёк. Внутри должен быть `tnsnames.ora` с псевдонимом `adb26ai_medium`.
3. В JDBC-клиенте строка подключения такая:

```text
jdbc:oracle:thin:@(description=(address=(protocol=tcps)(port=1522)(host=adb.eu-frankfurt-1.oraclecloud.com))(connect_data=(service_name=g37d999c93838e3_adb26ai_medium.adb.oraclecloud.com))(security=(ssl_server_dn_match=yes)))
```

В свойствах драйвера указать каталог кошелька (`TNS_ADMIN` или `oracle.net.wallet_location`) и пароль кошелька. Пользователь — `BMPUBLIC_BI`.

4. В Power BI и Tableau нужен Oracle Client той же разрядности, что и шлюз. Источник — псевдоним `adb26ai_medium` из `tnsnames.ora` кошелька.
5. В Python достаточно тонкого клиента `python-oracledb`: пользователь, пароль, `dsn="adb26ai_medium"`, каталог кошелька и пароль кошелька.
6. Первая проверка:

```sql
SELECT COUNT(*) FROM BMPUBLIC.TMS_UNIVERS;
```

На этом снимке ответ **4714**. Если архив на сервере позже обновят, число изменится. Тогда эталон — страница http://130.61.108.5/test-bi/ , она считает живую базу.

В модель BI попадает таблица или представление, либо короткий агрегирующий запрос. Журнал `TXSLD` целиком в Excel не выгружают: в нём 1 286 253 строки.

### 5. Таблицы, с которых начинается отчёт

Остальные сотни таблиц — карточки документов, зарплата, цены, договоры, маркетинг и служебные журналы. Их открывают, когда отчёт про этот предмет. Для первой работы хватает списка ниже.

| Таблица | Строк на снимке | Назначение |
| --- | --- | --- |
| `TMS_UNIVERS` | 4 714 | Общий справочник. Ключ — `COD`, название — `DENUMIREA`. Поле `TIP`: `O` организация, `P` продукция, `M` материал, `T` статья операции, `F` основное средство, `L` производство |
| `TMS_ORG` | карточка на код справочника | Реквизиты организации: адрес, банк, счета, фискальный код `CODFISCAL`, телефоны. Тот же `COD`, что у карточки типа `O` |
| `TMS_MUNC` | кадры | Карточка сотрудника |
| `TMS_SYSS` | классификатор | Короткие списки системы. Строка ищется по `TIP`, `COD`, `COD1` |
| `TMS_SYSF` | формы | Формы и операции документов. `ID` ссылается из `TMDB_DOCS.SYSFID` |
| `TMDB_DOCS` | 7 375 | Шапка документа: дата `DATAMANUAL`, номер `NRMANUAL`, журнал `TIP`, валюта `VALUTA`. В этой копии `CODF` у всех строк равен 0, контрагента в шапке нет |
| `TMDB_CM` | 122 003 | Проводки. В комментарии базы так и записано: `PROVODKI`. Одна строка — одна проводка: счета `DT` и `CT`, сумма `SUMA` в леях, валютная сумма и валюта, дата `DATA`, документ `NRDOC`, аналитика `DTSC`/`CTSC`, организация или подразделение `DTDEP`/`CTDEP` |
| `TXSLD` | 1 286 253 | Журнал движений. Для отчёта берут строки с датой в 2025–2026: их 55 426, почти все по продукции. У 1 230 800 строк даты нет. Ещё несколько строк имеют невозможный год (225, 1220, 5202). Такие строки в отчёт не входят |
| `TSLD`, `TSLDX` | 0 | Структура остатка. Живой остаток в архив BI не кладётся, таблицы оставлены пустыми |
| `TSLRPRM_CALCD`, `TSLRPRM_LINKM` | расчёт зарплаты | Строки расчёта, в том числе объектные суммы |
| `A$LOB` | 6 085 | Макеты форм. Текст переведён в UTF-8. Это не таблица фактов для оборота |

Связи, которые нужны в первых запросах:

* проводка `TMDB_CM.NRDOC` = документ `TMDB_DOCS.COD`;
* организация проводки `TMDB_CM.DTDEP` = карточка `TMS_UNIVERS.COD` с `TIP = 'O'`;
* аналитика `TMDB_CM.DTSC` или `CTSC` = карточка справочника, чаще продукция `P`, материал `M` или статья `T`;
* движение `TXSLD.SC` = карточка продукции.

Сумма `SUMA` — сумма проводки. Сложение всех проводок за месяц даёт оборот, а не прибыль. Август 2025 на этом снимке тяжёлый: около 15,1 млн леев при 1 645 проводках, это входной месяц копии.

### 6. Представления и зачем они

Представление — сохранённый запрос. Своих строк оно не хранит. Отчёт читает его, когда к коду уже подставлено название.

Читателю видны 782 годных представления. По имени они делятся так:

| Семейство | Годных | Зачем |
| --- | --- | --- |
| `VMS_*` | 154 | Лицо справочников. `VMS_UNIVERS` повторяет `TMS_UNIVERS` и добавляет подпись `DENUMIREA__1` и имя родителя по `CODI`. `VMS_ORG` повторяет реквизиты и расшифровывает город, категорию и банк через `VMS_SYSS`. `VMS_MUNC`, `VMS_SYSS`, `VMS_SYSF` — то же для кадров, классификатора и форм |
| `VMDB_*` | 218 | Лицо документов и проводок. `VMDB_DOCS` — шапка `TMDB_DOCS` плюс название операции, имя пользователя, вид документа, подразделение и статус. `V0CM` — проводки с `SPTYPE = 0`, дебет и кредит разложены по колонкам. `VMDB_CMI` добавляет цену `SUMA/CANT` и названия аналитики: `CLCDTDEPT`, `CLCDTSCT`, `CLCCTDEPT`, `CLCCTSCT` |
| `VSLR_*` | 40 | Зарплата. `VSLRPRM_CALCD` — карточка расчёта |
| `VCN_*` | 41 | Договоры |
| `VPR_*` | 19 | Прайс-листы |
| прочие | около 300 | Конкретные формы, маркетинг, производство. Их берут по имени предмета отчёта |

Часть представлений источника в эту базу не выдана: они были недействительны ещё до переноса (`AFIX_VSLD*`, `MAT_VSLD`, `VTMP_*`, `ZVMDB_CMR_ORIG` и соседние). В списке читателя их нет. Чинкой базы из BI студент не занимается.

Для первого отчёта достаточно `VMS_UNIVERS`, `VMDB_DOCS` и `VMDB_CMI`. Таблицу выбирают, когда нужны исходные коды без расшифровки. Представление выбирают, когда в отчёте должно быть название, а не число `COD`.

### 7. Задания

Ответы пишите в тетрадь или в файл. Запросы сохраняйте.

1. Своими словами опишите, какие права есть у `BMPUBLIC_BI` и почему отчёт не подключают учёткой `ADMIN`.
2. Подключитесь из DBeaver или другого клиента по разделу 4. Выполните четыре подсчёта и запишите числа:

```sql
SELECT COUNT(*) FROM BMPUBLIC.TMS_UNIVERS;
SELECT COUNT(*) FROM BMPUBLIC.TMDB_DOCS;
SELECT COUNT(*) FROM BMPUBLIC.TMDB_CM;
SELECT COUNT(*) FROM BMPUBLIC.TXSLD;
```

На снимке `20260930_1952` ожидаются 4714, 7375, 122003, 1286253. Сверьте те же четыре числа с http://130.61.108.5/test-bi/ .

3. Разложите справочник по типам:

```sql
SELECT TRIM(TIP) tip, COUNT(*) n
FROM BMPUBLIC.TMS_UNIVERS
GROUP BY TRIM(TIP)
ORDER BY n DESC;
```

Для каждого из `O`, `P`, `M`, `T`, `F` выпишите одно название из `DENUMIREA`.

4. Посчитайте документы по месяцам 2026 года и сравните столбцы с графиком на тестовой BI.

5. По проводкам июля 2026 посчитайте число строк и сумму `SUMA`. Рядом выпишите, что это оборот, а не прибыль.

6. Пять организаций с наибольшим числом проводок на дебете:

```sql
SELECT u.COD, u.DENUMIREA, COUNT(*) n
FROM BMPUBLIC.TMDB_CM c
JOIN BMPUBLIC.TMS_UNIVERS u
  ON u.COD = c.DTDEP AND TRIM(u.TIP) = 'O'
GROUP BY u.COD, u.DENUMIREA
ORDER BY COUNT(*) DESC
FETCH FIRST 5 ROWS ONLY;
```

7. По `TXSLD` отдельно посчитайте строки без даты и строки с датой от 01.01.2025 до 01.01.2027. Напишите, какой из двух наборов попадает в отчёт и почему.

8. Для одного `COD` сравните строку `TMDB_DOCS` и строку `VMDB_DOCS`. Перечислите колонки, которые добавляет представление.

9. Выполните `UPDATE BMPUBLIC.TMS_UNIVERS SET DENUMIREA = DENUMIREA WHERE COD = 0`. Вклейте текст ошибки Oracle. Откатывать нечего: строка не менялась.

10. Назовите два ограничения этой копии, из-за которых отчёт нельзя считать полной живой бухгалтерией.

### 8. Контрольные вопросы

1. Зачем соединению кошелёк и порт 1522?
2. Чем `SELECT` на конкретные объекты отличается от права менять строки?
3. Чем представление отличается от таблицы, если оба видны в списке источников BI?
4. Почему в этой копии контрагента нет в шапке документа?
5. Почему большой оборот августа 2025 нельзя складывать с остальными месяцами и называть результатом года без оговорки?

### 9. Сдача

Сдаётся файл с запросами, четырьмя числами из задания 2, текстом ошибки из задания 9 и короткими ответами на задания 1, 7 и 10. Пароль и кошелёк в файл не кладут.

---

<a id="ro"></a>

## Română

### 1. Scopul

Să conectați un BI extern la schema `BMPUBLIC` din Oracle Autonomous AI Database și să citiți un raport fără să modificați datele. La sfârșit explicați de ce pentru asta există un cont separat, doar pentru citire, și știți ce tabel sau ce vizualizare răspunde de ce.

Durata: 2–3 ore academice.

### 2. Ce s-a făcut deja cu baza

Sursa este Oracle 11.2, schema `BMPUBLIC` de pe serverul `cloudbd`. A fost mutată pe Autonomous AI Database `ADB26AI`, care există deja la Frankfurt. Setul de caractere al bazei din cloud este `AL32UTF8`. Este o copie pentru rapoarte, nu o a doua contabilitate de lucru.

La acest instantaneu cititorul vede **951 de tabele** și **782 de vizualizări** ale schemei `BMPUBLIC`, toate cu starea `VALID`. Alături există schema de mediu `UN4PUBLIC`. Schema străină `CRM_APP` nu a fost modificată la transfer. Ciornele `ZTEM*`, `ZTMP*`, `ZTEMP*` nu au intrat în copie.

Pentru accesul din afară a fost creat contul `BMPUBLIC_BI`. Are `CREATE SESSION` și `SELECT` pe tabelele și vizualizările `BMPUBLIC`. Nu are drepturi `ANY`, nu poate scrie și nu este administrator. Declanșatorul de intrare setează `NLS_DATE_FORMAT = DD.MM.YYYY` și `NLS_LENGTH_SEMANTICS = CHAR`.

Peste acest cont sunt două lucruri:

* pagina de conectare http://130.61.108.5/bi/ — cum se leagă DBeaver, Power BI, Tableau sau Python;
* BI-ul de test http://130.61.108.5/test-bi/ — un raport gata, în rusă, română și portugheză (Brazilia). Orice alt BI citește aceeași bază în același fel.

### 3. Un utilizator separat, doar pentru citire

Raportul se conectează cu contul `BMPUBLIC_BI`.

Așa se lucrează și mai departe. Contul de raport poate deschide o sesiune și poate citi obiectele primite. Nu inserează, nu actualizează și nu șterge rânduri și nu schimbă structura. O greșeală în interogare sau în setarea BI-ului nu strică înregistrările contabile.

Contul `ADMIN` nu se folosește pentru raport. Administratorul are obiecte din alte scheme, inclusiv `CRM_APP`. Un raport deschis ca administrator vede date străine și le poate modifica. Parola de administrator și parola portofelului nu se publică pe site. Studentul păstrează portofelul la el și nu îl trimite nicăieri.

Verificarea că contul este doar pentru citire: orice `UPDATE` sau `DELETE` pe `BMPUBLIC` trebuie să se termine cu o eroare de drepturi. Acesta este rezultatul așteptat.

### 4. Cum ia orice BI această bază ca sursă

Baza acceptă conexiunea prin TLS reciproc.

| Parametru | Valoare |
| --- | --- |
| Gazdă | `adb.eu-frankfurt-1.oraclecloud.com` |
| Port | `1522` |
| Protocol | `TCPS` |
| Serviciu | `g37d999c93838e3_adb26ai_medium.adb.oraclecloud.com` |
| Alias în portofel | `adb26ai_medium` |
| Schemă | `BMPUBLIC` |
| Utilizator | `BMPUBLIC_BI` |

Ordinea este aceeași pentru DBeaver, Power BI, Tableau, Excel și Python.

1. Primiți de la profesor arhiva portofelului, parola portofelului și parola `BMPUBLIC_BI`.
2. Despachetați portofelul. Înăuntru trebuie să fie `tnsnames.ora` cu aliasul `adb26ai_medium`.
3. Pentru un client JDBC șirul de conectare este:

```text
jdbc:oracle:thin:@(description=(address=(protocol=tcps)(port=1522)(host=adb.eu-frankfurt-1.oraclecloud.com))(connect_data=(service_name=g37d999c93838e3_adb26ai_medium.adb.oraclecloud.com))(security=(ssl_server_dn_match=yes)))
```

În proprietățile driverului indicați dosarul portofelului (`TNS_ADMIN` sau `oracle.net.wallet_location`) și parola portofelului. Utilizatorul este `BMPUBLIC_BI`.

4. Power BI și Tableau au nevoie de Oracle Client de aceeași capacitate ca gateway-ul. Sursa este aliasul `adb26ai_medium` din `tnsnames.ora` al portofelului.
5. În Python ajunge clientul subțire `python-oracledb`: utilizator, parolă, `dsn="adb26ai_medium"`, dosarul portofelului și parola portofelului.
6. Prima verificare:

```sql
SELECT COUNT(*) FROM BMPUBLIC.TMS_UNIVERS;
```

Pe acest instantaneu răspunsul este **4714**. Dacă arhiva de pe server este reînnoită mai târziu, numărul se schimbă. Atunci etalonul este pagina http://130.61.108.5/test-bi/ : ea numără baza vie.

În modelul BI intră un tabel sau o vizualizare, ori o interogare scurtă de agregare. Jurnalul `TXSLD` nu se exportă întreg în Excel: are 1 286 253 de rânduri.

### 5. Tabelele de la care începe raportul

Celelalte sute de tabele sunt fișe de documente, salarii, prețuri, contracte, marketing și jurnale tehnice. Se deschid când raportul este despre acel subiect. Pentru prima lucrare ajunge lista de mai jos.

| Tabel | Rânduri în instantaneu | Rol |
| --- | --- | --- |
| `TMS_UNIVERS` | 4 714 | Nomenclatorul general. Cheia este `COD`, denumirea este `DENUMIREA`. Câmpul `TIP`: `O` organizație, `P` produs, `M` material, `T` articol de operațiune, `F` mijloc fix, `L` producție |
| `TMS_ORG` | fișă pe codul nomenclatorului | Datele organizației: adresă, bancă, conturi, cod fiscal `CODFISCAL`, telefoane. Același `COD` ca la fișa de tip `O` |
| `TMS_MUNC` | cadre | Fișa angajatului |
| `TMS_SYSS` | clasificator | Listele scurte ale sistemului. Rândul se caută după `TIP`, `COD`, `COD1` |
| `TMS_SYSF` | formulare | Formularele și operațiunile documentelor. `ID` este referit din `TMDB_DOCS.SYSFID` |
| `TMDB_DOCS` | 7 375 | Antetul documentului: data `DATAMANUAL`, numărul `NRMANUAL`, jurnalul `TIP`, valuta `VALUTA`. În această copie `CODF` este 0 la toate rândurile, partenerul nu este în antet |
| `TMDB_CM` | 122 003 | Înregistrările contabile. Comentariul din bază spune `PROVODKI`. Un rând este o înregistrare: conturile `DT` și `CT`, suma `SUMA` în lei, suma în valută și valuta, data `DATA`, documentul `NRDOC`, analitica `DTSC`/`CTSC`, organizația sau subdiviziunea `DTDEP`/`CTDEP` |
| `TXSLD` | 1 286 253 | Jurnalul de mișcări. Pentru raport se iau rândurile cu dată în 2025–2026: sunt 55 426, aproape toate pe produse. La 1 230 800 de rânduri data lipsește. Câteva rânduri au un an imposibil (225, 1220, 5202). Acestea nu intră în raport |
| `TSLD`, `TSLDX` | 0 | Structura soldului. Soldul viu nu este pus în arhiva BI, tabelele au rămas goale |
| `TSLRPRM_CALCD`, `TSLRPRM_LINKM` | calculul salariului | Rândurile de calcul, inclusiv sumele de tip obiect |
| `A$LOB` | 6 085 | Machetele formularelor. Textul a fost trecut în UTF-8. Nu este tabelul de fapte pentru rulaj |

Legăturile necesare în primele interogări:

* înregistrarea `TMDB_CM.NRDOC` = documentul `TMDB_DOCS.COD`;
* organizația de la debit `TMDB_CM.DTDEP` = fișa `TMS_UNIVERS.COD` cu `TIP = 'O'`;
* analitica `TMDB_CM.DTSC` sau `CTSC` = o fișă din nomenclator, cel mai des produs `P`, material `M` sau articol `T`;
* mișcarea `TXSLD.SC` = fișa produsului.

Suma `SUMA` este suma înregistrării. Adunarea tuturor înregistrărilor dintr-o lună dă rulajul, nu profitul. August 2025 este luna grea a acestui instantaneu: circa 15,1 milioane de lei la 1 645 de înregistrări, luna de intrare a copiei.

### 6. Vizualizările și la ce folosesc

Vizualizarea este o interogare salvată. Nu își păstrează rândurile. Raportul o citește când lângă cod este deja pusă denumirea.

Cititorul vede 782 de vizualizări valide. După nume se împart așa:

| Familia | Valide | La ce folosesc |
| --- | --- | --- |
| `VMS_*` | 154 | Fața nomenclatoarelor. `VMS_UNIVERS` repetă `TMS_UNIVERS` și adaugă eticheta `DENUMIREA__1` și numele părintelui după `CODI`. `VMS_ORG` repetă datele și descifrează orașul, categoria și banca prin `VMS_SYSS`. `VMS_MUNC`, `VMS_SYSS`, `VMS_SYSF` fac același lucru pentru cadre, clasificator și formulare |
| `VMDB_*` | 218 | Fața documentelor și a înregistrărilor. `VMDB_DOCS` este antetul `TMDB_DOCS` plus denumirea operațiunii, numele utilizatorului, tipul documentului, subdiviziunea și starea. `V0CM` sunt înregistrările cu `SPTYPE = 0`, debitul și creditul sunt așezate pe coloane. `VMDB_CMI` adaugă prețul `SUMA/CANT` și denumirile analitice: `CLCDTDEPT`, `CLCDTSCT`, `CLCCTDEPT`, `CLCCTSCT` |
| `VSLR_*` | 40 | Salariile. `VSLRPRM_CALCD` este fișa de calcul |
| `VCN_*` | 41 | Contractele |
| `VPR_*` | 19 | Listele de prețuri |
| altele | circa 300 | Formulare concrete, marketing, producție. Se iau după subiectul raportului |

O parte din vizualizările sursei nu au fost acordate în această bază: erau nevalide încă înainte de transfer (`AFIX_VSLD*`, `MAT_VSLD`, `VTMP_*`, `ZVMDB_CMR_ORIG` și cele vecine). Nu sunt în lista cititorului. Studentul nu repară baza din BI.

Pentru primul raport ajung `VMS_UNIVERS`, `VMDB_DOCS` și `VMDB_CMI`. Tabelul se alege când sunt necesari codurile originale, fără descifrare. Vizualizarea se alege când în raport trebuie să fie denumirea, nu numărul `COD`.

### 7. Sarcini

Scrieți răspunsurile într-un caiet sau într-un fișier. Păstrați interogările.

1. Cu cuvintele voastre descrieți ce drepturi are `BMPUBLIC_BI` și de ce raportul nu se conectează cu contul `ADMIN`.
2. Conectați-vă din DBeaver sau din alt client după secțiunea 4. Executați patru numărări și notați valorile:

```sql
SELECT COUNT(*) FROM BMPUBLIC.TMS_UNIVERS;
SELECT COUNT(*) FROM BMPUBLIC.TMDB_DOCS;
SELECT COUNT(*) FROM BMPUBLIC.TMDB_CM;
SELECT COUNT(*) FROM BMPUBLIC.TXSLD;
```

Pe instantaneul `20260930_1952` se așteaptă 4714, 7375, 122003, 1286253. Verificați aceleași patru numere cu http://130.61.108.5/test-bi/ .

3. Împărțiți nomenclatorul pe tipuri:

```sql
SELECT TRIM(TIP) tip, COUNT(*) n
FROM BMPUBLIC.TMS_UNIVERS
GROUP BY TRIM(TIP)
ORDER BY n DESC;
```

Pentru fiecare dintre `O`, `P`, `M`, `T`, `F` scrieți o denumire din `DENUMIREA`.

4. Numărați documentele pe lunile anului 2026 și comparați coloanele cu graficul din BI-ul de test.

5. Pentru înregistrările din iulie 2026 calculați numărul de rânduri și suma `SUMA`. Scrieți alături că acesta este rulajul, nu profitul.

6. Cinci organizații cu cele mai multe înregistrări la debit:

```sql
SELECT u.COD, u.DENUMIREA, COUNT(*) n
FROM BMPUBLIC.TMDB_CM c
JOIN BMPUBLIC.TMS_UNIVERS u
  ON u.COD = c.DTDEP AND TRIM(u.TIP) = 'O'
GROUP BY u.COD, u.DENUMIREA
ORDER BY COUNT(*) DESC
FETCH FIRST 5 ROWS ONLY;
```

7. Pe `TXSLD` numărați separat rândurile fără dată și rândurile cu dată de la 01.01.2025 până la 01.01.2027. Scrieți care dintre cele două mulțimi intră în raport și de ce.

8. Pentru un același `COD` comparați un rând din `TMDB_DOCS` cu un rând din `VMDB_DOCS`. Enumerați coloanele pe care le adaugă vizualizarea.

9. Executați `UPDATE BMPUBLIC.TMS_UNIVERS SET DENUMIREA = DENUMIREA WHERE COD = 0`. Lipiți textul erorii Oracle. Nu este nimic de anulat: rândul nu s-a schimbat.

10. Numiți două limite ale acestei copii din cauza cărora raportul nu poate fi socotit contabilitatea vie și completă.

### 8. Întrebări de control

1. De ce conexiunea are nevoie de portofel și de portul 1522?
2. Cu ce se deosebește `SELECT` pe obiecte concrete de dreptul de a modifica rânduri?
3. Cu ce se deosebește vizualizarea de tabel, dacă ambele apar în lista de surse a BI-ului?
4. De ce în această copie partenerul nu este în antetul documentului?
5. De ce rulajul mare din august 2025 nu se adună cu celelalte luni și nu se numește rezultatul anului fără o precizare?

### 9. Predarea

Se predă un fișier cu interogările, cu cele patru numere de la sarcina 2, cu textul erorii de la sarcina 9 și cu răspunsuri scurte la sarcinile 1, 7 și 10. Parola și portofelul nu se pun în fișier.

---

<a id="en"></a>

## English

### 1. Aim

Connect an external BI tool to the `BMPUBLIC` schema on Oracle Autonomous AI Database and read a report without changing the data. By the end you can explain why a separate read-only account is used, and you know which table or view is for which job.

Time: 2–3 class hours.

### 2. What has already been done with the database

The source is Oracle 11.2, schema `BMPUBLIC`, on the server `cloudbd`. It was copied onto the Autonomous AI Database `ADB26AI`, which already exists in Frankfurt. The cloud database character set is `AL32UTF8`. This is a copy for reports, not a second live accounting system.

On this snapshot the reader can see **951 tables** and **782 views** in schema `BMPUBLIC`, all `VALID`. The environment schema `UN4PUBLIC` sits beside it. The unrelated schema `CRM_APP` was not changed by the copy. Draft tables `ZTEM*`, `ZTMP*` and `ZTEMP*` were not loaded.

The external account is `BMPUBLIC_BI`. It has `CREATE SESSION` and `SELECT` on the `BMPUBLIC` tables and views. It has no `ANY` privileges, no write privileges and no administrator privileges. The logon trigger sets `NLS_DATE_FORMAT = DD.MM.YYYY` and `NLS_LENGTH_SEMANTICS = CHAR`.

Two things sit on top of that account:

* the connection page http://130.61.108.5/bi/ — how to connect DBeaver, Power BI, Tableau or Python;
* the test BI at http://130.61.108.5/test-bi/ — one finished report, in Russian, Romanian and Brazilian Portuguese. Any other BI tool reads the same database in the same way.

### 3. A separate read-only user

The report connects as `BMPUBLIC_BI`.

That is the account to keep using. The report account can open a session and read the objects it was granted. It does not insert, update or delete rows, and it does not change the structure. A mistake in a query or in the BI settings does not damage the ledger.

The `ADMIN` account is not used for a report. The administrator can see objects in other schemas, including `CRM_APP`. A report opened as administrator shows data that does not belong to the report and can change it. The administrator password and the wallet password are not published on the site. You keep the wallet locally and do not send it anywhere.

The check that the account is read-only: any `UPDATE` or `DELETE` on `BMPUBLIC` must end with a privilege error. That error is the expected result.

### 4. How any BI tool uses this database as a source

The database accepts a mutual TLS connection.

| Setting | Value |
| --- | --- |
| Host | `adb.eu-frankfurt-1.oraclecloud.com` |
| Port | `1522` |
| Protocol | `TCPS` |
| Service | `g37d999c93838e3_adb26ai_medium.adb.oraclecloud.com` |
| Wallet alias | `adb26ai_medium` |
| Schema | `BMPUBLIC` |
| User | `BMPUBLIC_BI` |

The steps are the same for DBeaver, Power BI, Tableau, Excel and Python.

1. Get the wallet archive, the wallet password and the `BMPUBLIC_BI` password from the teacher.
2. Unpack the wallet. It must contain `tnsnames.ora` with the alias `adb26ai_medium`.
3. For a JDBC client the connect string is:

```text
jdbc:oracle:thin:@(description=(address=(protocol=tcps)(port=1522)(host=adb.eu-frankfurt-1.oraclecloud.com))(connect_data=(service_name=g37d999c93838e3_adb26ai_medium.adb.oraclecloud.com))(security=(ssl_server_dn_match=yes)))
```

In the driver properties set the wallet directory (`TNS_ADMIN` or `oracle.net.wallet_location`) and the wallet password. The user is `BMPUBLIC_BI`.

4. Power BI and Tableau need an Oracle Client of the same bitness as the gateway. The source is the alias `adb26ai_medium` from the wallet `tnsnames.ora`.
5. Python only needs the thin `python-oracledb` driver: user, password, `dsn="adb26ai_medium"`, the wallet directory and the wallet password.
6. First check:

```sql
SELECT COUNT(*) FROM BMPUBLIC.TMS_UNIVERS;
```

On this snapshot the answer is **4714**. If the archive on the server is refreshed later, the number changes. The reference is then the page http://130.61.108.5/test-bi/ , which counts the live database.

A BI model is given a table, a view, or a short aggregate query. Do not export the whole `TXSLD` journal into Excel: it has 1,286,253 rows.

### 5. Tables a report starts from

The other hundreds of tables are document cards, payroll, prices, contracts, marketing and technical logs. Open them when the report is about that subject. The first session only needs the list below.

| Table | Rows on the snapshot | Role |
| --- | --- | --- |
| `TMS_UNIVERS` | 4,714 | The shared catalog. The key is `COD`, the name is `DENUMIREA`. Column `TIP`: `O` organization, `P` product, `M` material, `T` operation article, `F` fixed asset, `L` production |
| `TMS_ORG` | one card per catalog code | Organization details: address, bank, accounts, fiscal code `CODFISCAL`, phones. The same `COD` as a card of type `O` |
| `TMS_MUNC` | personnel | Employee card |
| `TMS_SYSS` | classifier | Short system lists. A row is found by `TIP`, `COD`, `COD1` |
| `TMS_SYSF` | forms | Document forms and operations. `ID` is referenced from `TMDB_DOCS.SYSFID` |
| `TMDB_DOCS` | 7,375 | Document header: date `DATAMANUAL`, number `NRMANUAL`, journal `TIP`, currency `VALUTA`. In this copy `CODF` is 0 on every row, so the partner is not in the header |
| `TMDB_CM` | 122,003 | Ledger entries. The database comment on the table is `PROVODKI`. One row is one entry: accounts `DT` and `CT`, amount `SUMA` in lei, currency amount and currency, date `DATA`, document `NRDOC`, analytics `DTSC`/`CTSC`, organization or department `DTDEP`/`CTDEP` |
| `TXSLD` | 1,286,253 | Movement journal. A report uses the rows dated in 2025–2026: there are 55,426 of them, almost all products. 1,230,800 rows have no date. A few rows have an impossible year (225, 1220, 5202). Those rows stay out of the report |
| `TSLD`, `TSLDX` | 0 | Balance structure. The live balance is not put in the BI archive, so the tables were left empty |
| `TSLRPRM_CALCD`, `TSLRPRM_LINKM` | payroll calculation | Calculation rows, including object amounts |
| `A$LOB` | 6,085 | Form designs. The text was converted to UTF-8. This is not the fact table for turnover |

Joins used in the first queries:

* entry `TMDB_CM.NRDOC` = document `TMDB_DOCS.COD`;
* the organization on the entry, `TMDB_CM.DTDEP`, = catalog card `TMS_UNIVERS.COD` with `TIP = 'O'`;
* analytics `TMDB_CM.DTSC` or `CTSC` = a catalog card, most often a product `P`, a material `M` or an article `T`;
* movement `TXSLD.SC` = the product card.

`SUMA` is the amount of one entry. Adding every entry in a month gives turnover, not profit. August 2025 is the heavy month of this snapshot: about 15.1 million lei in 1,645 entries. That is the opening month of the copy.

### 6. Views and what they are for

A view is a stored query. It does not keep rows of its own. A report reads a view when the name has already been placed next to the code.

The reader can see 782 valid views. By name they fall into these groups:

| Family | Valid | What they are for |
| --- | --- | --- |
| `VMS_*` | 154 | The face of the catalogs. `VMS_UNIVERS` repeats `TMS_UNIVERS` and adds the label `DENUMIREA__1` and the parent name through `CODI`. `VMS_ORG` repeats the details and decodes city, category and bank through `VMS_SYSS`. `VMS_MUNC`, `VMS_SYSS` and `VMS_SYSF` do the same for personnel, the classifier and forms |
| `VMDB_*` | 218 | The face of documents and entries. `VMDB_DOCS` is the `TMDB_DOCS` header plus the operation name, the user name, the document type, the division and the status. `V0CM` is the entries with `SPTYPE = 0`, with debit and credit laid out in columns. `VMDB_CMI` adds the price `SUMA/CANT` and the analytics names: `CLCDTDEPT`, `CLCDTSCT`, `CLCCTDEPT`, `CLCCTSCT` |
| `VSLR_*` | 40 | Payroll. `VSLRPRM_CALCD` is the calculation card |
| `VCN_*` | 41 | Contracts |
| `VPR_*` | 19 | Price lists |
| other | about 300 | Individual forms, marketing, production. Take one when the report is about that subject |

Some source views were not granted on this database: they were already invalid before the copy (`AFIX_VSLD*`, `MAT_VSLD`, `VTMP_*`, `ZVMDB_CMR_ORIG` and their neighbours). They are not in the reader's list. You do not repair the database from a BI tool.

The first report only needs `VMS_UNIVERS`, `VMDB_DOCS` and `VMDB_CMI`. Choose the table when you need the original codes without decoding. Choose the view when the report must show a name rather than the number `COD`.

### 7. Tasks

Write the answers in a notebook or a file. Keep the queries.

1. In your own words, describe the privileges of `BMPUBLIC_BI` and why a report is not connected as `ADMIN`.
2. Connect from DBeaver or another client, following section 4. Run the four counts and write down the numbers:

```sql
SELECT COUNT(*) FROM BMPUBLIC.TMS_UNIVERS;
SELECT COUNT(*) FROM BMPUBLIC.TMDB_DOCS;
SELECT COUNT(*) FROM BMPUBLIC.TMDB_CM;
SELECT COUNT(*) FROM BMPUBLIC.TXSLD;
```

On snapshot `20260930_1952` the expected values are 4714, 7375, 122003 and 1286253. Check the same four numbers against http://130.61.108.5/test-bi/ .

3. Split the catalog by type:

```sql
SELECT TRIM(TIP) tip, COUNT(*) n
FROM BMPUBLIC.TMS_UNIVERS
GROUP BY TRIM(TIP)
ORDER BY n DESC;
```

For each of `O`, `P`, `M`, `T` and `F`, write one name from `DENUMIREA`.

4. Count documents by month for 2026 and compare the bars with the chart on the test BI.

5. For the July 2026 entries, calculate the row count and the sum of `SUMA`. Write next to it that this is turnover, not profit.

6. Five organizations with the most entries on the debit side:

```sql
SELECT u.COD, u.DENUMIREA, COUNT(*) n
FROM BMPUBLIC.TMDB_CM c
JOIN BMPUBLIC.TMS_UNIVERS u
  ON u.COD = c.DTDEP AND TRIM(u.TIP) = 'O'
GROUP BY u.COD, u.DENUMIREA
ORDER BY COUNT(*) DESC
FETCH FIRST 5 ROWS ONLY;
```

7. On `TXSLD`, count separately the rows with no date and the rows dated from 1 January 2025 up to 1 January 2027. Write which of the two sets goes into a report, and why.

8. For one `COD`, compare a row of `TMDB_DOCS` with a row of `VMDB_DOCS`. List the columns the view adds.

9. Run `UPDATE BMPUBLIC.TMS_UNIVERS SET DENUMIREA = DENUMIREA WHERE COD = 0`. Paste the Oracle error text. There is nothing to roll back: the row was not changed.

10. Name two limits of this copy that stop a report from being treated as the full live accounting system.

### 8. Check questions

1. Why does the connection need a wallet and port 1522?
2. How is `SELECT` on named objects different from the right to change rows?
3. How is a view different from a table when both appear in the BI source list?
4. Why is the partner missing from the document header in this copy?
5. Why must the large August 2025 turnover not be added to the other months and called the year's result without a note?

### 9. What to hand in

Hand in a file with the queries, the four numbers from task 2, the error text from task 9, and short answers to tasks 1, 7 and 10. Do not put the password or the wallet in the file.

---

<a id="pt-br"></a>

## Português (Brasil)

Para questões no Brasil, fale com **Ivan Souza**.

Senior Software Engineer & Technical Lead | Delphi / Object Pascal Legacy System Modernization Specialist

Juiz de Fora, Brazil (Open to Remote / International)

[+55 (43) 99102-5152](tel:+5543991025152) · [ilsouza@gmail.com](mailto:ilsouza@gmail.com) · [linkedin.com/in/ivanlsouza](https://www.linkedin.com/in/ivanlsouza)

**Resumo profissional**

Senior Software Engineer with 20+ years modernizing business-critical Delphi / Object Pascal systems - Unicode and 64-bit migrations with additional hands-on experience in C++, C# and modern software engineering practices, BDE to FireDAC data layers, replacement of discontinued third-party components, and incremental Delphi-to-.NET / Delphi-to-Web transitions. I work at the difficult end of legacy: codebases that cannot be rewritten, cannot go down, and have to keep running while they change. That means reading twenty-year-old code carefully, planning migrations that ship in stages, and leaving a codebase a maintaining team can actually own. Technical lead experience across distributed, cross-timezone teams in Brazil, Italy, Poland and Belgium - setting architecture direction, reviewing code, and mentoring developers. Fluent in English. After 20 years in consulting, seeking a permanent, fully remote Senior Delphi Engineer or Technical Lead role with an employer outside Brazil.

### 1. Objetivo

Conectar um BI externo ao schema `BMPUBLIC` no Oracle Autonomous AI Database e ler um relatório sem alterar os dados. No fim, você explica por que existe um usuário separado, só de leitura, e sabe qual tabela ou view serve para quê.

Duração: 2 a 3 horas-aula.

### 2. O que já foi feito com o banco

A origem é o Oracle 11.2, schema `BMPUBLIC`, no servidor `cloudbd`. Ele foi copiado para o Autonomous AI Database `ADB26AI`, que já existia em Frankfurt. O conjunto de caracteres do banco na nuvem é `AL32UTF8`. Esta é uma cópia para relatórios, não uma segunda contabilidade em produção.

Neste instantâneo o leitor vê **951 tabelas** e **782 views** do schema `BMPUBLIC`, todas com status `VALID`. Ao lado existe o schema de ambiente `UN4PUBLIC`. O schema alheio `CRM_APP` não foi alterado na cópia. Os rascunhos `ZTEM*`, `ZTMP*` e `ZTEMP*` não entraram.

Para o acesso externo foi criado o usuário `BMPUBLIC_BI`. Ele tem `CREATE SESSION` e `SELECT` nas tabelas e views de `BMPUBLIC`. Não tem privilégios `ANY`, não grava e não é administrador. A trigger de logon define `NLS_DATE_FORMAT = DD.MM.YYYY` e `NLS_LENGTH_SEMANTICS = CHAR`.

Em cima desse usuário há duas coisas:

* a página de conexão http://130.61.108.5/bi/ — como conectar o DBeaver, o Power BI, o Tableau ou o Python;
* o BI de teste http://130.61.108.5/test-bi/ — um relatório pronto, em russo, romeno e português (Brasil). Qualquer outro BI lê o mesmo banco do mesmo jeito.

### 3. Um usuário separado, só de leitura

O relatório conecta com o usuário `BMPUBLIC_BI`.

É esse usuário que se usa daqui para a frente. A conta do relatório abre sessão e lê os objetos que recebeu. Ela não insere, não atualiza e não apaga linhas, e não muda a estrutura. Um erro na consulta ou na configuração do BI não estraga os lançamentos.

A conta `ADMIN` não entra no relatório. O administrador enxerga objetos de outros schemas, inclusive `CRM_APP`. Um relatório aberto como administrador mostra dados que não são do relatório e pode alterá-los. A senha de administrador e a senha da carteira não são publicadas no site. Você guarda a carteira (wallet) na sua máquina e não a envia para lugar nenhum.

A prova de que a conta é só de leitura: qualquer `UPDATE` ou `DELETE` em `BMPUBLIC` tem de terminar com erro de privilégio. Esse erro é o resultado esperado.

### 4. Como qualquer BI usa este banco como fonte

O banco aceita conexão com TLS mútuo.

| Parâmetro | Valor |
| --- | --- |
| Host | `adb.eu-frankfurt-1.oraclecloud.com` |
| Porta | `1522` |
| Protocolo | `TCPS` |
| Serviço | `g37d999c93838e3_adb26ai_medium.adb.oraclecloud.com` |
| Alias na carteira | `adb26ai_medium` |
| Schema | `BMPUBLIC` |
| Usuário | `BMPUBLIC_BI` |

A ordem é a mesma no DBeaver, no Power BI, no Tableau, no Excel e no Python.

1. Receba do professor o arquivo da carteira, a senha da carteira e a senha do `BMPUBLIC_BI`.
2. Descompacte a carteira. Dentro dela precisa existir `tnsnames.ora` com o alias `adb26ai_medium`.
3. Num cliente JDBC a string de conexão é:

```text
jdbc:oracle:thin:@(description=(address=(protocol=tcps)(port=1522)(host=adb.eu-frankfurt-1.oraclecloud.com))(connect_data=(service_name=g37d999c93838e3_adb26ai_medium.adb.oraclecloud.com))(security=(ssl_server_dn_match=yes)))
```

Nas propriedades do driver informe a pasta da carteira (`TNS_ADMIN` ou `oracle.net.wallet_location`) e a senha da carteira. O usuário é `BMPUBLIC_BI`.

4. Power BI e Tableau precisam do Oracle Client com a mesma quantidade de bits do gateway. A fonte é o alias `adb26ai_medium` do `tnsnames.ora` da carteira.
5. No Python basta o driver fino `python-oracledb`: usuário, senha, `dsn="adb26ai_medium"`, a pasta da carteira e a senha da carteira.
6. Primeira verificação:

```sql
SELECT COUNT(*) FROM BMPUBLIC.TMS_UNIVERS;
```

Neste instantâneo a resposta é **4714**. Se o arquivo no servidor for atualizado depois, o número muda. A referência passa a ser a página http://130.61.108.5/test-bi/ , que conta o banco ao vivo.

O modelo do BI recebe uma tabela, uma view ou uma consulta curta de agregação. Não exporte o diário `TXSLD` inteiro para o Excel: ele tem 1.286.253 linhas.

### 5. Tabelas por onde o relatório começa

As outras centenas de tabelas são fichas de documento, folha, preços, contratos, marketing e logs técnicos. Abra uma delas quando o relatório for sobre esse assunto. Na primeira aula basta a lista abaixo.

| Tabela | Linhas no instantâneo | Função |
| --- | --- | --- |
| `TMS_UNIVERS` | 4.714 | Cadastro geral. A chave é `COD`, o nome é `DENUMIREA`. A coluna `TIP`: `O` organização, `P` produto, `M` material, `T` artigo de operação, `F` ativo imobilizado, `L` produção |
| `TMS_ORG` | uma ficha por código do cadastro | Dados da organização: endereço, banco, contas, código fiscal `CODFISCAL`, telefones. O mesmo `COD` da ficha de tipo `O` |
| `TMS_MUNC` | pessoal | Ficha do funcionário |
| `TMS_SYSS` | classificador | Listas curtas do sistema. A linha se acha por `TIP`, `COD`, `COD1` |
| `TMS_SYSF` | formulários | Formulários e operações dos documentos. `ID` é referenciado em `TMDB_DOCS.SYSFID` |
| `TMDB_DOCS` | 7.375 | Cabeçalho do documento: data `DATAMANUAL`, número `NRMANUAL`, diário `TIP`, moeda `VALUTA`. Nesta cópia `CODF` é 0 em todas as linhas, então o parceiro não está no cabeçalho |
| `TMDB_CM` | 122.003 | Lançamentos contábeis. O comentário da tabela no banco é `PROVODKI`. Uma linha é um lançamento: contas `DT` e `CT`, valor `SUMA` em lei, valor em moeda e a moeda, data `DATA`, documento `NRDOC`, analítica `DTSC`/`CTSC`, organização ou departamento `DTDEP`/`CTDEP` |
| `TXSLD` | 1.286.253 | Diário de movimentos. O relatório usa as linhas com data em 2025–2026: são 55.426, quase todas de produto. 1.230.800 linhas não têm data. Algumas linhas têm um ano impossível (225, 1220, 5202). Essas ficam fora do relatório |
| `TSLD`, `TSLDX` | 0 | Estrutura do saldo. O saldo vivo não entra no arquivo de BI, então as tabelas ficaram vazias |
| `TSLRPRM_CALCD`, `TSLRPRM_LINKM` | cálculo da folha | Linhas de cálculo, inclusive valores de tipo objeto |
| `A$LOB` | 6.085 | Modelos de formulário. O texto foi convertido para UTF-8. Não é a tabela fato do movimento |

As ligações das primeiras consultas:

* lançamento `TMDB_CM.NRDOC` = documento `TMDB_DOCS.COD`;
* a organização no lançamento, `TMDB_CM.DTDEP`, = ficha `TMS_UNIVERS.COD` com `TIP = 'O'`;
* a analítica `TMDB_CM.DTSC` ou `CTSC` = uma ficha do cadastro, na maior parte produto `P`, material `M` ou artigo `T`;
* movimento `TXSLD.SC` = a ficha do produto.

`SUMA` é o valor de um lançamento. Somar todos os lançamentos de um mês dá o movimento, não o lucro. Agosto de 2025 é o mês pesado deste instantâneo: cerca de 15,1 milhões de lei em 1.645 lançamentos. É o mês de abertura da cópia.

### 6. Views e para que servem

Uma view é uma consulta salva. Ela não guarda linhas próprias. O relatório lê a view quando o nome já foi colocado ao lado do código.

O leitor vê 782 views válidas. Pelo nome elas se dividem assim:

| Família | Válidas | Para que servem |
| --- | --- | --- |
| `VMS_*` | 154 | A face dos cadastros. `VMS_UNIVERS` repete `TMS_UNIVERS` e acrescenta o rótulo `DENUMIREA__1` e o nome do pai por `CODI`. `VMS_ORG` repete os dados e decodifica cidade, categoria e banco por `VMS_SYSS`. `VMS_MUNC`, `VMS_SYSS` e `VMS_SYSF` fazem o mesmo para pessoal, classificador e formulários |
| `VMDB_*` | 218 | A face dos documentos e dos lançamentos. `VMDB_DOCS` é o cabeçalho de `TMDB_DOCS` mais o nome da operação, o nome do usuário, o tipo do documento, o departamento e o status. `V0CM` são os lançamentos com `SPTYPE = 0`, débito e crédito dispostos em colunas. `VMDB_CMI` acrescenta o preço `SUMA/CANT` e os nomes da analítica: `CLCDTDEPT`, `CLCDTSCT`, `CLCCTDEPT`, `CLCCTSCT` |
| `VSLR_*` | 40 | Folha de pagamento. `VSLRPRM_CALCD` é a ficha de cálculo |
| `VCN_*` | 41 | Contratos |
| `VPR_*` | 19 | Listas de preço |
| outras | cerca de 300 | Formulários específicos, marketing, produção. Use uma quando o relatório for sobre esse assunto |

Algumas views da origem não foram concedidas neste banco: já estavam inválidas antes da cópia (`AFIX_VSLD*`, `MAT_VSLD`, `VTMP_*`, `ZVMDB_CMR_ORIG` e as vizinhas). Elas não aparecem na lista do leitor. Você não conserta o banco a partir do BI.

O primeiro relatório só precisa de `VMS_UNIVERS`, `VMDB_DOCS` e `VMDB_CMI`. Escolha a tabela quando precisar dos códigos originais, sem decodificação. Escolha a view quando o relatório tiver de mostrar o nome, e não o número `COD`.

### 7. Tarefas

Escreva as respostas num caderno ou num arquivo. Guarde as consultas.

1. Com as suas palavras, descreva os privilégios de `BMPUBLIC_BI` e por que o relatório não conecta como `ADMIN`.
2. Conecte pelo DBeaver ou por outro cliente, seguindo a seção 4. Execute as quatro contagens e anote os números:

```sql
SELECT COUNT(*) FROM BMPUBLIC.TMS_UNIVERS;
SELECT COUNT(*) FROM BMPUBLIC.TMDB_DOCS;
SELECT COUNT(*) FROM BMPUBLIC.TMDB_CM;
SELECT COUNT(*) FROM BMPUBLIC.TXSLD;
```

No instantâneo `20260930_1952` os valores esperados são 4714, 7375, 122003 e 1286253. Confira os mesmos quatro números em http://130.61.108.5/test-bi/ .

3. Separe o cadastro por tipo:

```sql
SELECT TRIM(TIP) tip, COUNT(*) n
FROM BMPUBLIC.TMS_UNIVERS
GROUP BY TRIM(TIP)
ORDER BY n DESC;
```

Para cada um de `O`, `P`, `M`, `T` e `F`, escreva um nome de `DENUMIREA`.

4. Conte os documentos por mês de 2026 e compare as barras com o gráfico do BI de teste.

5. Nos lançamentos de julho de 2026, calcule a quantidade de linhas e a soma de `SUMA`. Escreva ao lado que isso é movimento, não lucro.

6. Cinco organizações com mais lançamentos no débito:

```sql
SELECT u.COD, u.DENUMIREA, COUNT(*) n
FROM BMPUBLIC.TMDB_CM c
JOIN BMPUBLIC.TMS_UNIVERS u
  ON u.COD = c.DTDEP AND TRIM(u.TIP) = 'O'
GROUP BY u.COD, u.DENUMIREA
ORDER BY COUNT(*) DESC
FETCH FIRST 5 ROWS ONLY;
```

7. Em `TXSLD`, conte à parte as linhas sem data e as linhas com data de 1º de janeiro de 2025 até 1º de janeiro de 2027. Escreva qual dos dois conjuntos entra no relatório, e por quê.

8. Para um mesmo `COD`, compare uma linha de `TMDB_DOCS` com uma linha de `VMDB_DOCS`. Liste as colunas que a view acrescenta.

9. Execute `UPDATE BMPUBLIC.TMS_UNIVERS SET DENUMIREA = DENUMIREA WHERE COD = 0`. Cole o texto do erro do Oracle. Não há o que desfazer: a linha não mudou.

10. Cite dois limites desta cópia que impedem tratar o relatório como a contabilidade viva e completa.

### 8. Perguntas de controle

1. Por que a conexão precisa da carteira e da porta 1522?
2. Em que `SELECT` sobre objetos nomeados difere do direito de alterar linhas?
3. Em que uma view difere de uma tabela, se as duas aparecem na lista de fontes do BI?
4. Por que, nesta cópia, o parceiro não está no cabeçalho do documento?
5. Por que o movimento grande de agosto de 2025 não se soma aos outros meses e não se chama resultado do ano sem uma ressalva?

### 9. O que entregar

Entregue um arquivo com as consultas, os quatro números da tarefa 2, o texto do erro da tarefa 9 e respostas curtas às tarefas 1, 7 e 10. Não coloque a senha nem a carteira no arquivo.
