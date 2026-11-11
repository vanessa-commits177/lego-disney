"""Met à jour data.json et promos.json (et alerts.md en cas de bonne affaire).
Chaque jour : pages liste Brickfact (meilleur prix, remise, retrait proche) + promos.
Chaque mardi (ou lancement manuel) : fiches Brickfact (sortie, retrait, boutiques) + annonces eBay.fr.
Secrets optionnels : EBAY_ID, EBAY_SECRET (annonces eBay), BRICKSET_KEY (dates précises de sortie et de retrait)."""
import base64, datetime as dt, html, json, os, re, time
from pathlib import Path
import requests

TODAY = dt.date.today()
BF = "https://brickfact.com"
HDR = {"User-Agent": "Mozilla/5.0 (suivi personnel LEGO Disney, peu de requêtes)"}
STATE, OUT, PRO = Path("state.json"), Path("data.json"), Path("promos.json")
state = json.loads(STATE.read_text()) if STATE.exists() else {}
for k, v in (("sets", {}), ("ids", {}), ("hist", {}), ("alerted", {})):
    state.setdefault(k, v)
ALERT_PCT = 30  # alerte si un set bientôt retiré passe sous −30 % du prix conseillé
FR = ("amazon.fr", "fnac", "darty", "cdiscount", "joybuy", "brickeez", "cultura", "carrefour",
      "leclerc", "auchan", "intermarché", "king jouet", "joué club", "jouéclub",
      "grande récré", "maxi toys", "micromania", "lego.fr")
EMPTY = {"count": None, "min": None, "gone7": 0, "gone30": 0}


def get(url):
    time.sleep(1.5)  # on reste poli avec le site
    r = requests.get(url, headers=HDR, timeout=30)
    r.raise_for_status()
    return r.text


def txt(h):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", h))).strip()


def eur(x):
    x = x.replace("\xa0", "").replace(" ", "")
    return float(x.replace(".", "").replace(",", ".")) if "," in x else float(x)


# ---------- Quotidien : pages liste Brickfact ----------
A = re.compile(r'<a[^>]+href="((?:https://brickfact\.com)?/fr-fr/sets/[^"]+)"[^>]*>(.*?)</a>', re.S)
L = re.compile(r"(\d{4,6}) Disney™ \1 (.+?) livraison incluse de ?([\d.,]+) ?€ "
               r"Prix conseillé ([\d.,]+) ?€ (\d+) offres?")


def listing():
    out = {}
    for page in range(1, 12):
        n0 = len(out)
        for href, inner in A.findall(get(f"{BF}/fr-fr/themes/disney/{page}")):
            t = txt(inner)
            m = L.search(t)
            if not m:
                continue
            num, name, best, rrp, n = m.groups()
            best, rrp = eur(best), eur(rrp)
            out[num] = {"name": name, "url": href if href.startswith("http") else BF + href,
                        "best": best, "rrp": rrp, "offers": int(n),
                        "pct": round(100 * (1 - best / rrp)) if best < rrp else 0,
                        "eol_soon": "Bientôt retiré" in t}
        if len(out) == n0:
            break
    return out


# ---------- Hebdomadaire : fiche d'un set (dates, boutiques françaises) ----------
O = re.compile(r'<a[^>]+title="Offre Lego \d+ chez ([^"]+)"[^>]*>(.*?)</a>', re.S)


def fiche(url):
    h = get(url)
    t = txt(h)
    d = {}
    m = re.search(r"Année (\d{2}/\d{4})", t)
    d["launch"] = m.group(1) if m else None
    m = re.search(r"EOL Statut (.+?) (?:Informations sur les prix|RRP)", t)
    d["exit"] = m.group(1) if m else None
    shops = {}
    for shop, inner in O.findall(h):
        if any(k in shop.lower() for k in FR):
            m = re.search(r"([\d.,]+) ?€", txt(inner))
            if m:
                shops[shop] = eur(m.group(1))  # premier prix affiché = livraison incluse
    m = re.search(r"Lego\.fr ([\d.,]+) ?€", t)
    if m:
        shops["Lego.fr"] = eur(m.group(1))
    d["shops"] = shops
    return d


# ---------- Hebdomadaire : annonces eBay.fr ----------
def ebay_token():
    cred = f'{os.environ["EBAY_ID"]}:{os.environ["EBAY_SECRET"]}'.encode()
    r = requests.post("https://api.ebay.com/identity/v1/oauth2/token",
                      headers={"Authorization": "Basic " + base64.b64encode(cred).decode(),
                               "Content-Type": "application/x-www-form-urlencoded"},
                      data={"grant_type": "client_credentials",
                            "scope": "https://api.ebay.com/oauth/api_scope"}, timeout=30)
    r.raise_for_status()
    return r.json()["access_token"]


def ebay(tok, num, cond):
    r = requests.get("https://api.ebay.com/buy/browse/v1/item_summary/search",
                     headers={"Authorization": "Bearer " + tok, "X-EBAY-C-MARKETPLACE-ID": "EBAY_FR"},
                     params={"q": f"LEGO {num}", "category_ids": "19006", "limit": 200,
                             "filter": f"conditions:{{{cond}}},itemLocationCountry:FR"}, timeout=30)
    r.raise_for_status()
    j = r.json()
    items = j.get("itemSummaries", [])
    prices = [float(i["price"]["value"]) for i in items if i.get("price", {}).get("currency") == "EUR"]
    return j.get("total", len(items)), [i["itemId"] for i in items], (min(prices) if prices else None)


def brickset():
    k = os.environ["BRICKSET_KEY"]
    h = ""
    if os.environ.get("BRICKSET_USER"):  # connexion facultative, si Brickset réclame un « userHash »
        r = requests.get("https://brickset.com/api/v3.asmx/login",
                         params={"apiKey": k, "username": os.environ["BRICKSET_USER"],
                                 "password": os.environ["BRICKSET_PASS"]}, timeout=30)
        h = r.json().get("hash", "")
    r = requests.get("https://brickset.com/api/v3.asmx/getSets",
                     params={"apiKey": k, "userHash": h,
                             "params": json.dumps({"theme": "Disney", "pageSize": 500})}, timeout=60)
    r.raise_for_status()
    j = r.json()
    if j.get("status") != "success":
        raise RuntimeError(j.get("message"))
    return {s["number"]: {"launch_date": (s.get("launchDate") or "")[:10] or None,
                          "exit_date": (s.get("exitDate") or "")[:10] or None}
            for s in j.get("sets", [])}


# ---------- Promos générales sur les jouets (fichier promos_jouets.json, rempli à la main) ----------
def jouets(sets):
    try:
        promos = json.loads(Path("promos_jouets.json").read_text())
    except Exception:
        return []
    out = []
    for p in promos:
        if not (p.get("du", "0000") <= TODAY.isoformat() <= p.get("au", "9999")):
            continue
        rows = []
        for num, s in sets.items():
            # prix de l'enseigne si Brickfact la connaît, sinon prix conseillé LEGO
            price = next((v for k, v in (s.get("shops") or {}).items()
                          if p["enseigne"].lower() in k.lower()), s.get("rrp"))
            if price and price >= p["seuil"]:
                net = price - p["remise"]
                rows.append({"num": num, "name": s["name"], "net": round(net, 2),
                             "pct": round(100 * (1 - net / s["rrp"])) if s.get("rrp") else 0,
                             "eol": bool(s.get("eol_soon"))})
        rows.sort(key=lambda r: (not r["eol"], -r["pct"]))
        out.append({**p, "sets": rows[:8]})
    return out


# ---------- Programme ----------
FULL = bool(os.environ.get("FULL")) or TODAY.weekday() == 1 or not OUT.exists()
alerts = []
try:
    for num, v in listing().items():
        state["sets"].setdefault(num, {}).update(v)
        if v["eol_soon"] and v["pct"] >= ALERT_PCT:
            if v["pct"] >= state["alerted"].get(num, 0) + 10:
                state["alerted"][num] = v["pct"]
                alerts.append(f'- {num} {v["name"]} : {v["best"]:.2f} € (−{v["pct"]} %), retrait proche, {v["url"]}')
        else:
            state["alerted"].pop(num, None)
except Exception as e:
    print("Pages liste indisponibles :", e)

if FULL:
    tok = None
    if os.environ.get("EBAY_ID"):
        try:
            tok = ebay_token()
        except Exception as e:
            print("eBay indisponible :", e)
    try:
        if os.environ.get("BRICKSET_KEY"):
            bs = brickset()
            for num, s in state["sets"].items():
                s.update(bs.get(num, {}))
    except Exception as e:
        print("Brickset indisponible :", e)
    for num, s in sorted(state["sets"].items()):
        try:
            s.update(fiche(s["url"]))
        except Exception as e:
            print(num, "fiche :", e)
        for cond, key in (("NEW", "new"), ("USED", "used")):
            if not tok:
                break
            k = f"{num}:{key}"
            try:
                total, ids, low = ebay(tok, num, cond)
                prev = set(state["ids"].get(k, []))
                gone = len(prev - set(ids)) if prev else 0  # annonces vues la semaine passée et disparues
                state["ids"][k] = ids
                h = state["hist"].setdefault(k, [])
                h.append({"d": TODAY.isoformat(), "gone": gone})
                del h[:-8]
                s[key] = {"count": total, "min": low, "gone7": sum(x["gone"] for x in h[-1:]),
                          "gone30": sum(x["gone"] for x in h[-4:])}
            except Exception as e:
                print(num, key, "eBay :", e)

rows = [{"num": n, **{k: s.get(k) for k in ("name", "launch", "exit", "launch_date", "exit_date", "rrp", "best", "pct", "offers", "eol_soon", "shops")},
         "new": s.get("new") or EMPTY, "used": s.get("used") or EMPTY}
        for n, s in sorted(state["sets"].items())]
OUT.write_text(json.dumps({"updated": TODAY.isoformat(), "sets": rows}, ensure_ascii=False, indent=1))

top = sorted((s for s in state["sets"].values() if s.get("pct", 0) >= 25), key=lambda s: -s["pct"])[:10]
J = jouets(state["sets"])
for j in J:
    key = f'{j["enseigne"]}|{j.get("du")}'
    if key not in state["alerted"]:
        state["alerted"][key] = 1
        alerts.append(f'- Promo {j["enseigne"]} : {j["libelle"]} (jusqu’au {j.get("au", "?")})')
PRO.write_text(json.dumps({"updated": TODAY.isoformat(), "jouets": J,
                           "items": [{"num": n, "name": s["name"], "price": s["best"], "pct": s["pct"],
                                      "eol": s["eol_soon"]} for n, s in state["sets"].items() if s in top]},
                          ensure_ascii=False, indent=1))
STATE.write_text(json.dumps(state))
if alerts:
    Path("alerts.md").write_text("Nouvelles bonnes affaires détectées :\n\n" + "\n".join(alerts) + "\n")
print(len(rows), "sets ;", len(alerts), "alerte(s)")
