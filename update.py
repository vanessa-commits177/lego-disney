"""Met à jour data.json et promos.json.
Chaque mardi (ou lancement manuel) : Brickset (liste, dates, prix conseillé) + annonces eBay.fr.
Chaque jour : promos générales sur les jouets (fichier promos_jouets.json) + alertes.
Secrets : BRICKSET_KEY (obligatoire) ; BRICKSET_USER et BRICKSET_PASS (seulement si Brickset
réclame une connexion) ; EBAY_ID et EBAY_SECRET (facultatifs, sans eux pas de données eBay)."""
import base64, datetime as dt, json, os
from pathlib import Path
import requests

TODAY = dt.date.today()
STATE, OUT, PRO = Path("state.json"), Path("data.json"), Path("promos.json")
state = json.loads(STATE.read_text()) if STATE.exists() else {}
for k, v in (("sets", {}), ("ids", {}), ("hist", {}), ("alerted", {})):
    state.setdefault(k, v)
EMPTY = {"count": None, "min": None, "gone7": 0, "gone30": 0}


# ---------- Brickset : liste des sets Disney, dates, prix conseillé ----------
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
    out = {}
    for s in j.get("sets", []):
        if s.get("year", 0) < 2023:
            continue
        de = (s.get("LEGOCom") or {}).get("DE") or {}  # prix conseillé en euros (LEGO.com zone euro)
        out[s["number"]] = {"name": s["name"], "year": s["year"], "rrp": de.get("retailPrice"),
                            "launch_date": (s.get("launchDate") or "")[:10] or None,
                            "exit_date": (s.get("exitDate") or "")[:10] or None}
    return out


# ---------- eBay.fr : annonces (API officielle) ----------
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


# ---------- Promos générales sur les jouets (fichier promos_jouets.json, rempli à la main) ----------
def soon(s):  # retrait passé ou dans les 6 mois
    d = s.get("exit_date")
    return bool(d) and dt.date.fromisoformat(d) <= TODAY + dt.timedelta(days=183)


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
            price = s.get("rrp")  # on suppose le prix en rayon = prix conseillé LEGO
            if price and price >= p["seuil"]:
                net = price - p["remise"]
                rows.append({"num": num, "name": s["name"], "net": round(net, 2),
                             "pct": round(100 * (1 - net / price)), "eol": soon(s)})
        rows.sort(key=lambda r: (not r["eol"], -r["pct"]))
        out.append({**p, "sets": rows[:8]})
    return out


# ---------- Programme ----------
FULL = bool(os.environ.get("FULL")) or TODAY.weekday() == 1 or not OUT.exists()
if FULL:
    try:
        for num, v in brickset().items():
            state["sets"].setdefault(num, {}).update(v)
    except Exception as e:
        print("Brickset indisponible :", e)
    tok = None
    if os.environ.get("EBAY_ID"):
        try:
            tok = ebay_token()
        except Exception as e:
            print("eBay indisponible :", e)
    for num, s in sorted(state["sets"].items()):
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
    rows = [{"num": n, **{k: s.get(k) for k in ("name", "year", "launch_date", "exit_date", "rrp")},
             "new": s.get("new") or EMPTY, "used": s.get("used") or EMPTY}
            for n, s in sorted(state["sets"].items())]
    OUT.write_text(json.dumps({"updated": TODAY.isoformat(), "sets": rows}, ensure_ascii=False, indent=1))

alerts = []
J = jouets(state["sets"])
for j in J:
    key = f'{j["enseigne"]}|{j.get("du")}'
    if key not in state["alerted"]:
        state["alerted"][key] = 1
        alerts.append(f'- Promo {j["enseigne"]} : {j["libelle"]} (jusqu’au {j.get("au", "?")})')
PRO.write_text(json.dumps({"updated": TODAY.isoformat(), "jouets": J}, ensure_ascii=False, indent=1))
STATE.write_text(json.dumps(state))
if alerts:
    Path("alerts.md").write_text("Nouvelle promo jouets détectée :\n\n" + "\n".join(alerts) + "\n")
print(len(state["sets"]), "sets ;", len(alerts), "alerte(s)")
