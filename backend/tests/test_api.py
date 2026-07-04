"""API happy paths via FastAPI TestClient (AUTH_DISABLED=1 set in conftest)."""
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

BIRTH = {
    "date": "1990-05-15",
    "time": "06:30",
    "lat": 12.9716,
    "lon": 77.5946,
    "tz_offset": 5.5,
    "place_name": "Bengaluru",
}


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_chart():
    r = client.post("/api/chart", json={"birth": BIRTH})
    assert r.status_code == 200
    data = r.json()
    assert set(data["planets"].keys()) == {
        "Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn",
        "Rahu", "Ketu"}
    assert 0 <= data["lagna"]["sign"] <= 11
    assert len(data["houses"]) == 12
    for p in data["planets"].values():
        assert 1 <= p["house"] <= 12
        assert p["dignity"] in {"exalted", "moolatrikona", "own", "friend",
                                "neutral", "enemy", "debilitated"}


def test_vargas():
    r = client.post("/api/vargas", json={"birth": BIRTH, "charts": ["D9", "D10"]})
    assert r.status_code == 200
    assert set(r.json()["vargas"].keys()) == {"D9", "D10"}


def test_dashas():
    r = client.post("/api/dashas", json={"birth": BIRTH, "on": "2026-07-03"})
    assert r.status_code == 200
    data = r.json()
    assert data["tree"]["periods"]
    assert len(data["active"]) == 3


def test_transits():
    r = client.post("/api/transits", json={"birth": BIRTH, "on": "2026-07-03"})
    assert r.status_code == 200
    data = r.json()
    assert len(data["gochara"]) == 9
    assert "sade_sati" in data and "double_transit" in data


def test_yogas():
    r = client.post("/api/yogas", json={"birth": BIRTH})
    assert r.status_code == 200
    assert isinstance(r.json()["yogas"], list)


def test_ashtakavarga():
    r = client.post("/api/ashtakavarga", json={"birth": BIRTH})
    assert r.status_code == 200
    assert r.json()["sav_total"] == 337


def test_predictions():
    r = client.post("/api/predictions", json={"birth": BIRTH, "on": "2026-07-03"})
    assert r.status_code == 200
    data = r.json()
    areas = {a["area"] for a in data["areas"]}
    assert {"career", "wealth", "health", "relationships", "family",
            "education"} <= areas
    for a in data["areas"]:
        assert -1.0 <= a["score"] <= 1.0
        assert a["trend"] in ("improving", "stable", "challenging")
        assert isinstance(a["substantiation"], list)


def test_interpret_template():
    r = client.post("/api/interpret", json={"birth": BIRTH, "provider": "template"})
    assert r.status_code == 200
    data = r.json()
    assert data["provider"] == "template"
    assert data["text"]
    assert data["citations"]


def test_rectify():
    r = client.post("/api/rectify", json={
        "birth": BIRTH,
        "window_minutes": 10,
        "step_minutes": 5,
        "events": [{"type": "marriage", "date": "2015-02-10"}],
    })
    assert r.status_code == 200
    data = r.json()
    assert data["n_candidates"] == 5
    assert data["candidates"][0]["score"] >= data["candidates"][-1]["score"]


def test_panchanga():
    r = client.post("/api/panchanga", json={"birth": BIRTH})
    assert r.status_code == 200
    data = r.json()
    assert 1 <= data["tithi"]["number"] <= 30
    assert data["vara"]["name"].endswith("vara")
    assert data["nakshatra"]["name"]
    assert 1 <= data["yoga"]["number"] <= 27
    assert data["karana"]["name"]
    assert data["sunrise"] and data["sunset"]


def test_matching():
    bride = dict(BIRTH, date="1992-11-02", time="14:45")
    r = client.post("/api/matching", json={"groom": BIRTH, "bride": bride})
    assert r.status_code == 200
    data = r.json()
    assert len(data["kutas"]) == 8
    assert 0 <= data["total"] <= 36
    assert data["verdict"]
    assert "mangal_dosha" in data


def test_panchanga_with_seconds_and_ayanamsa():
    birth = dict(BIRTH, time="06:30:45")
    r = client.post("/api/panchanga",
                    json={"birth": birth, "config": {"ayanamsa": "raman"}})
    assert r.status_code == 200
    assert r.json()["ayanamsa"] == "raman"


def test_shadbala():
    r = client.post("/api/shadbala", json={"birth": BIRTH})
    assert r.status_code == 200
    data = r.json()
    assert set(data["planets"].keys()) == {
        "Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"}
    for p in data["planets"].values():
        assert 0 < p["total_rupas"] < 12
        assert p["required_rupas"] > 0
        assert isinstance(p["sufficient"], bool)
        for comp in ("sthana", "dig", "kala", "cheshta", "naisargika", "drik"):
            assert comp in p


def test_jaimini():
    r = client.post("/api/jaimini", json={"birth": BIRTH, "on": "2026-07-03"})
    assert r.status_code == 200
    data = r.json()
    assert len(data["karakas"]) == 7
    assert data["karakas"][0]["karaka"] == "Atmakaraka"
    assert data["chara_dasha"]["direction"] in ("direct", "reverse")
    assert len(data["chara_dasha"]["periods"]) >= 12
    maha = data["chara_dasha"]["periods"][0]
    assert len(maha["children"]) == 12
    assert data["active"] and data["active"][0]["level_name"] == "mahadasha"


def test_validation_error():
    bad = dict(BIRTH, date="15-05-1990")
    r = client.post("/api/chart", json={"birth": bad})
    assert r.status_code == 422
