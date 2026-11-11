"""Met à jour data.json : sets LEGO Disney, dates, prix conseillé, annonces eBay.fr.
Variables d'environnement : BRICKSET_KEY, EBAY_ID, EBAY_SECRET."""
import base64, datetime as dt, json, os, re
from pathlib import Path
import requests

TODAY = dt.date.today()
STATE, OUT = Path("state.json"), Path("data.json")
state = json.loads(STATE.read_text()) if STATE.exists() else {"meta": {}, "ids": {}, "hist": {}}


def brickset():
    r = requests.get(
        "https://brickset.com/api/v3.asmx/getSets",
        params={"apiKey": os.environ["BRICKSET_KEY"], "userHash": "",
                "params": json.dumps({"theme": "Disney", "pageSize": 500})},
        timeout=60)
    r.raise_for_status()
    meta = {}
    for s in r.json().get("sets", []):
        if s.get("year", 0) < 2023:
            continue
        de = (s.get("LEGOCom") or {}).get("DE") or {}
        meta[s["number"]] = {
            "name": s["name"], "year": s["year"],
            "launch": (s.get("launchDate") or "")[:10] or None,
            "exit": (s.get("exitDate") or "")[:10] or None,
            "rrp": de.get("retailPrice"),  # prix conseillé en euros (LEGO.com zone euro)
        }
    return meta


def ebay_token():
    cred = f'{os.environ["EBAY_ID"]}:{os.environ["EBAY_SECRET"]}'.encode()
    r = requests.post(
        "https://api.ebay.com/identity/v1/oauth2/token",
        headers={"Authorization": "Basic " + base64.b64encode(cred).decode(),
                 "Content-Type": "application/x-www-form-urlencoded"},
        data={"grant_type": "client_credentials",
              "scope": "https://api.ebay.com/oauth/api_scope"},
        timeout=30)
    r.raise_for_status()
    return r.json()["access_token"]


def ebay(tok, num, cond):
    r = requests.get(
        "https://api.ebay.com/buy/browse/v1/item_summary/search",
        headers={"Authorization": "Bearer " + tok,
                 "X-EBAY-C-MARKETPLACE-ID": "EBAY_FR"},
        params={"q": f"LEGO {num}", "category_ids": "19006", "limit": 200,
                "filter": f"conditions:{{{cond}}},itemLocationCountry:FR"},
        timeout=30)
    r.raise_for_status()
    j = r.json()
    items = j.get("itemSummaries", [])
    prices = [float(i["price"]["value"]) for i in items
              if i.get("price", {}).get("currency") == "EUR"]
    return j.get("total", len(items)), [i["itemId"] for i in items], \
        (min(prices) if prices else None)


PROMO_RE = re.compile(
    r"(\d{5})\s*([^|]{3,90}?)\s*\|+\s*(\d+[.,]\d{2})\s*€\s*\|+\s*([^|]+?)\s*\|+\s*"
    r"(\d+[.,]\d{2})\s*€\s*\|+\s*[−-]\s*(\d+)\s*%")


def promos():
    # Offres du jour lues sur Brickfact (comparateur français) : à vérifier au premier lancement
    items = []
    try:
        r = requests.get("https://brickfact.com/fr-fr/themes/disney/1",
                         headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
        r.raise_for_status()
        txt = re.sub(r"<[^>]+>", "|", r.text)
        seen = set()
        for n, name, price, shop, rrp, pct in PROMO_RE.findall(txt):
            if n in seen:
                continue
            seen.add(n)
            f = lambda x: float(x.replace(",", "."))
            items.append({"num": n, "name": name.strip(), "price": f(price),
                          "shop": shop.strip(), "rrp": f(rrp), "pct": int(pct)})
    except Exception as e:
        print("Promos indisponibles :", e)
    if items:
        Path("promos.json").write_text(json.dumps(
            {"updated": TODAY.isoformat(), "items": items}, ensure_ascii=False, indent=1))
    else:
        print("Aucune promo lue : promos.json inchangé")


# Chaque jour : promos seulement. Chaque mardi (ou lancement manuel) : tout le reste.
FULL = bool(os.environ.get("FULL")) or TODAY.weekday() == 1 or not OUT.exists()
if not FULL:
    promos()
    raise SystemExit

if FULL:
    try:
        state["meta"] = brickset()
    except Exception as e:
        print("Brickset indisponible :", e)

tok = ebay_token()
rows = []
for num, m in sorted(state["meta"].items()):
    row = {"num": num, **m}
    for cond, key in (("NEW", "new"), ("USED", "used")):
        k = f"{num}:{key}"
        try:
            total, ids, low = ebay(tok, num, cond)
            prev = set(state["ids"].get(k, []))
            # annonces vues lors du relevé précédent (il y a une semaine) et disparues aujourd'hui = ventes estimées (ou retraits)
            gone = len(prev - set(ids)) if prev else 0
            state["ids"][k] = ids
            h = state["hist"].setdefault(k, [])
            h.append({"d": TODAY.isoformat(), "gone": gone})
            del h[:-8]
        except Exception as e:
            print(num, key, "erreur :", e)
            total, low = None, None
        h = state["hist"].get(k, [])
        row[key] = {"count": total, "min": low,
                    "gone7": sum(x["gone"] for x in h[-1:]),
                    "gone30": sum(x["gone"] for x in h[-4:])}
    rows.append(row)

OUT.write_text(json.dumps({"updated": TODAY.isoformat(), "sets": rows},
                          ensure_ascii=False, indent=1))
STATE.write_text(json.dumps(state))
print(len(rows), "sets mis à jour")
promos()
