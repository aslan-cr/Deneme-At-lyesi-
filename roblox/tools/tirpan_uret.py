#!/usr/bin/env python3
"""
Tırpan biçme animasyonu üretici (R6).

Hareketi üst seviye eğrilerle tanımlar (gövde dönüşü, eğilme, çökme, tırpan ucunun
gideceği yer), sonra her kare için:
  - bacakları ayaklar yerde kalacak şekilde yerleştirir,
  - iki elin de tırpan sapını tutacağı kol açılarını çözer.
Çıktı:  roblox/TirpanAnimasyonu_Olustur.lua  ve (istenirse) önizleme için JSON.

Kullanım:  python3 roblox/tools/tirpan_uret.py [onizleme.json]
Tırpanın yeri oyundaki Tool'dan ölçüldü ("normal tırpan", Grip = CFrame(0,-1.4,0) * X'te -15°,
standart RightGrip): sap sağ kolun yerel X ekseni boyunca (yana) uzanır ve avucun ~1,4 stud
önünde durur; bıçak sapın +X ucundan, kolun uzandığı yöne doğru çıkar. Yani tırpan kolun
devamı gibi savrulur. Animasyon oyundaki "toolnone" duruşuyla (sağ kol öne 90°) başlar ve biter.
"""
import json, math, os, sys
import numpy as np

FPS = 30
SURE = 1.6
KES_T = 0.5
# --- Tırpanın sağ kol uzayındaki yeri (kol parçasının merkezine göre; Studio'da ölçüldü) ---
SAP_Y, SAP_Z = -0.64, -1.35               # sap ekseninin geçtiği yer; sap kolun X ekseni boyunca uzanır
SAP_YARI = 1.8                            # sapın yarı uzunluğu (Handle 3.6 stud)
BICAK_X = 1.55                            # bıçağın sapa bağlandığı yer (sap üzerinde, +X ucu)
BICAK_YON = np.array([0, -0.966, -0.259]) # bıçağın uzandığı yön (kol uzayında; ele doğru, biraz öne)
BICAK_BOY = 3.0                           # bıçak kökünden ucuna
SOL_EL = np.array([0, -0.9, 1.0])         # sol elin duracağı yer: sağ elin hemen yanında (kol uzayında)
X_DINLEN = np.array([math.pi / 2, 0, 0, 0, 0, 0.0])  # "toolnone": sağ kol öne 90°, sol kol serbest
YER = -3.0               # kök parçaya göre zemin yüksekliği

def Rx(a): c, s = math.cos(a), math.sin(a); return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])
def Ry(a): c, s = math.cos(a), math.sin(a); return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])
def Rz(a): c, s = math.cos(a), math.sin(a); return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])
def norm(v): return v / (np.linalg.norm(v) + 1e-12)
def rodrigues(r):
    th = np.linalg.norm(r)
    if th < 1e-9: return np.eye(3)
    k = r / th
    K = np.array([[0, -k[2], k[1]], [k[2], 0, -k[0]], [-k[1], k[0], 0]])
    return np.eye(3) + math.sin(th) * K + (1 - math.cos(th)) * K @ K
def quat(R):
    t = np.trace(R)
    if t > 0:
        s = math.sqrt(t + 1) * 2; q = [(R[2, 1] - R[1, 2]) / s, (R[0, 2] - R[2, 0]) / s, (R[1, 0] - R[0, 1]) / s, s / 4]
    elif R[0, 0] > R[1, 1] and R[0, 0] > R[2, 2]:
        s = math.sqrt(1 + R[0, 0] - R[1, 1] - R[2, 2]) * 2; q = [s / 4, (R[0, 1] + R[1, 0]) / s, (R[0, 2] + R[2, 0]) / s, (R[2, 1] - R[1, 2]) / s]
    elif R[1, 1] > R[2, 2]:
        s = math.sqrt(1 + R[1, 1] - R[0, 0] - R[2, 2]) * 2; q = [(R[0, 1] + R[1, 0]) / s, s / 4, (R[1, 2] + R[2, 1]) / s, (R[0, 2] - R[2, 0]) / s]
    else:
        s = math.sqrt(1 + R[2, 2] - R[0, 0] - R[1, 1]) * 2; q = [(R[0, 2] + R[2, 0]) / s, (R[1, 2] + R[2, 1]) / s, s / 4, (R[1, 0] - R[0, 1]) / s]
    return np.array(q)

# ---------------- Hareket eğrileri ----------------
# don: gövde sağa dönüş (+), egil: öne eğilme, yan: sola yatma, cok: kalça alçalması,
# geri: kalçanın geriye kayması, diz: tek diz çökme (0-1),
# yon: bıçak ucunun (sağ omuzdan bakınca) yönü (0 = ileri, + = sağ, 180 = arka), yuk: bıçağın yerden yüksekliği,
# duz: bıçağın yere yatık olma isteği (0-1), dinlen: oyundaki "toolnone" duruşuna yakınlık (1 = tam o duruş)
ANAHTAR = [
    dict(t=0.00, ad="Bel",    dur=1, don=0,   egil=0,  yan=0,  cok=0.00, geri=0.0,  diz=0,   yon=20,  yuk=3.0,  duz=0,   dinlen=1),
    dict(t=0.25, ad="Geri",   dur=1, don=45,  egil=6,  yan=-4, cok=0.20, geri=0.2,  diz=0,   yon=125, yuk=1.7,  duz=0.6, dinlen=0),
    dict(t=0.42, ad="Savur",  dur=0, don=15,  egil=28, yan=4,  cok=0.75, geri=0.0,  diz=0.7, yon=80,  yuk=0.45, duz=1,   dinlen=0),
    dict(t=0.50, ad="Kes",    dur=0, don=-15, egil=38, yan=6,  cok=1.00, geri=-0.1, diz=1,   yon=30,  yuk=0.3,  duz=1,   dinlen=0),
    dict(t=0.64, ad="",       dur=0, don=-50, egil=41, yan=8,  cok=1.08, geri=-0.1, diz=1,   yon=-45, yuk=0.3,  duz=1,   dinlen=0),
    dict(t=0.80, ad="Bekle",  dur=1, don=-45, egil=37, yan=6,  cok=1.05, geri=-0.1, diz=1,   yon=-40, yuk=0.35, duz=1,   dinlen=0),
    dict(t=1.00, ad="",       dur=1, don=-42, egil=35, yan=5,  cok=1.02, geri=-0.1, diz=1,   yon=-37, yuk=0.4,  duz=1,   dinlen=0),
    dict(t=1.30, ad="Kalk",   dur=0, don=-10, egil=14, yan=0,  cok=0.30, geri=0.0,  diz=0.2, yon=5,   yuk=1.8,  duz=0.2, dinlen=0.5),
    dict(t=1.60, ad="Bitis",  dur=1, don=0,   egil=0,  yan=0,  cok=0.00, geri=0.0,  diz=0,   yon=20,  yuk=3.0,  duz=0,   dinlen=1),
]
ALANLAR = ["don", "egil", "yan", "cok", "geri", "diz", "duz", "dinlen", "yon", "yuk"]

def vektor(k): return np.array([k[a] for a in ALANLAR], dtype=float)
P = [vektor(k) for k in ANAHTAR]
T = [k["t"] for k in ANAHTAR]
def tanjant(i):
    if ANAHTAR[i]["dur"] or i == 0 or i == len(P) - 1: return np.zeros_like(P[i])
    return (P[i + 1] - P[i - 1]) / (T[i + 1] - T[i - 1])
M = [tanjant(i) for i in range(len(P))]
def egri(t):
    i = max(j for j in range(len(T) - 1) if T[j] <= t + 1e-9)
    h = T[i + 1] - T[i]; s = min(max((t - T[i]) / h, 0), 1)
    h00, h10, h01, h11 = 2*s**3 - 3*s**2 + 1, s**3 - 2*s**2 + s, -2*s**3 + 3*s**2, s**3 - s**2
    v = h00 * P[i] + h10 * h * M[i] + h01 * P[i + 1] + h11 * h * M[i + 1]
    d = dict(zip(ALANLAR, v))
    d["diz"] = min(max(d["diz"], 0), 1); d["duz"] = min(max(d["duz"], 0), 1)
    d["dinlen"] = min(max(d["dinlen"], 0), 1)
    return d

# ---------------- İskelet ----------------
OMUZ = {"R": np.array([1, 0.5, 0.0]), "L": np.array([-1, 0.5, 0.0])}
KOL_MERKEZ = {"R": np.array([0.5, -0.5, 0.0]), "L": np.array([-0.5, -0.5, 0.0])}
EL = {"R": np.array([0.5, -1.5, 0.0]), "L": np.array([-0.5, -1.5, 0.0])}   # omuz eklemine göre el
KALCA = {"R": np.array([0.5, -1, 0.0]), "L": np.array([-0.5, -1, 0.0])}

def govde(p):
    R = Rx(-math.radians(p["egil"])) @ Rz(math.radians(p["yan"])) @ Ry(-math.radians(p["don"]))
    kalca = np.array([0, -1 - p["cok"], p["geri"]])
    return R, kalca + R @ np.array([0, 1.0, 0])

def bacak(p, Rt, pt, taraf):
    """Ayak yerde kalacak şekilde bacak (kök uzayında dönüş ve merkez)."""
    kalca = pt + Rt @ KALCA[taraf]
    h = min(max(kalca[1] - YER, 0.35), 2.0)
    d = math.sqrt(max(4 - h * h, 0))
    yon = norm(np.array([-0.25, 0, -1.0])) if taraf == "L" else norm(np.array([0.3, 0, 1.0]))  # sol ayak önde
    alt = np.array([kalca[0], YER, kalca[2]]) + yon * d
    u = norm(kalca - alt)
    if taraf == "L" and p["diz"] > 0:   # öndeki bacak: diz çökerken dik durur (diz yukarıda görünür)
        k = p["diz"]
        alt_k = np.array([kalca[0] - 0.15, YER, kalca[2] - 1.25])
        u_k = norm(np.array([0.0, 1.0, 0.14]))
        alt = alt * (1 - k) + alt_k * k
        u = norm(u * (1 - k) + u_k * k)
    bakis = Ry(-math.radians(p["don"]) * 0.5) @ np.array([0, 0, -1.0])
    z = -bakis; z = norm(z - (z @ u) * u)
    R = np.column_stack([np.cross(u, z), u, z])
    return R, alt + u * 1.0

def kol_noktasi(RR, q):
    """Sağ kol uzayındaki (kol merkezine göre) bir noktayı gövde uzayına çevirir."""
    return OMUZ["R"] + RR @ (KOL_MERKEZ["R"] + q)

def kol_durum(x):
    RR, RL = rodrigues(x[:3]), rodrigues(x[3:])
    elR = OMUZ["R"] + RR @ EL["R"]; elL = OMUZ["L"] + RL @ EL["L"]
    kok = kol_noktasi(RR, np.array([BICAK_X, SAP_Y, SAP_Z]))      # bıçağın sapa bağlandığı yer
    uc = kok + RR @ BICAK_YON * BICAK_BOY                          # bıçağın ucu
    return RR, RL, elR, elL, kok, uc

UC_UZAKLIK = float(np.linalg.norm(KOL_MERKEZ["R"] + np.array([BICAK_X, SAP_Y, SAP_Z]) + BICAK_YON * BICAK_BOY))

def kutuda(pt, yari, pay):
    d = np.maximum(yari + pay - np.abs(pt), 0)
    return float(np.min(d)) if np.all(d > 0) else 0.0

def maliyet(x, Rt, pt, p, onceki):
    RR, RL, elR, elL, kok, uc = kol_durum(x)
    w = 1 - p["dinlen"]
    uc_g = Rt.T @ (p["uc"] - pt)                         # hedef, gövde uzayında
    e = w * 1.0 * np.sum((uc - uc_g) ** 2)
    # sol el sağ elin yanında dursun
    e += w * 14.0 * np.sum((elL - kol_noktasi(RR, SOL_EL)) ** 2)
    # bıçak yere yatık: sap dik (bıçaklı ucu aşağıda), bıçak kökü de istenen yükseklikte
    if p["duz"] > 0:
        asagi = -(Rt @ RR @ np.array([1.0, 0, 0]))[1]
        e += w * 5.0 * p["duz"] * (1 - asagi)
        e += w * 3.0 * p["duz"] * ((pt + Rt @ kok)[1] - (YER + p["yuk"])) ** 2
    # çarpışmalar: eller, sap ve bıçak gövdenin / kafanın içinden geçmesin, yere girmesin
    for el in (elR, elL):
        e += 30 * w * kutuda(el, np.array([1.0, 1.0, 0.5]), 0.35) ** 2
    noktalar = [kol_noktasi(RR, np.array([lm, SAP_Y, SAP_Z])) for lm in np.linspace(-SAP_YARI, SAP_YARI, 7)]
    noktalar += [kok + (uc - kok) * k for k in (0.33, 0.66, 1.0)]
    for q in noktalar:
        e += 12 * w * kutuda(q, np.array([1.0, 1.0, 0.5]), 0.2) ** 2
        e += 12 * w * max(0.85 - np.linalg.norm(q - np.array([0, 1.6, 0])), 0) ** 2
        yer = (pt + Rt @ q)[1] - (YER + 0.1)
        e += 6 * w * min(yer, 0) ** 2
    e += 40.0 * p["dinlen"] * np.sum((x - X_DINLEN) ** 2)   # baş/son: oyundaki duruşa yaklaş
    if onceki is not None:
        e += 0.06 * np.sum((x - onceki) ** 2)
    return e

def nelder_mead(f, x0, adim=0.35, tur=700):
    n = len(x0)
    S = [np.array(x0, float)] + [np.array(x0, float) + adim * np.eye(n)[i] for i in range(n)]
    F = [f(s) for s in S]
    for _ in range(tur):
        o = np.argsort(F); S = [S[i] for i in o]; F = [F[i] for i in o]
        if abs(F[-1] - F[0]) < 1e-10: break
        c = np.mean(S[:-1], axis=0)
        xr = c + (c - S[-1]); fr = f(xr)
        if fr < F[0]:
            xe = c + 2 * (c - S[-1]); fe = f(xe)
            S[-1], F[-1] = (xe, fe) if fe < fr else (xr, fr)
        elif fr < F[-2]:
            S[-1], F[-1] = xr, fr
        else:
            xc = c + 0.5 * (S[-1] - c); fc = f(xc)
            if fc < F[-1]: S[-1], F[-1] = xc, fc
            else:
                S = [S[0]] + [S[0] + 0.5 * (s - S[0]) for s in S[1:]]; F = [F[0]] + [f(s) for s in S[1:]]
    i = int(np.argmin(F)); return S[i], F[i]

def coz(Rt, pt, p, onceki, rng):
    f = lambda x: maliyet(x, Rt, pt, p, onceki)
    if onceki is not None:
        x, fx = nelder_mead(f, onceki, 0.15)
        x, fx = nelder_mead(f, x, 0.05)
        return x, fx
    en = (None, 1e9)
    for _ in range(60):
        x, fx = nelder_mead(lambda x: maliyet(x, Rt, pt, p, None), rng.uniform(-1.6, 1.6, 6))
        x, fx = nelder_mead(lambda x: maliyet(x, Rt, pt, p, None), x, 0.1)
        if fx < en[1]: en = (x, fx)
    return en

def kafa(p, Rt, pt, uc_dunya):
    bas = pt + Rt @ np.array([0, 1.5, 0])
    hedef = norm(0.45 * np.array([0, -0.15, -1.0]) + 0.55 * norm(uc_dunya - bas))
    v = Rt.T @ hedef
    w = 1 - p["dinlen"]
    yaw = w * float(np.clip(math.atan2(-v[0], -v[2]), -1.2, 1.2))
    pitch = w * float(np.clip(math.asin(np.clip(v[1], -1, 1)), -0.6, 0.5))
    R = Ry(yaw) @ Rx(pitch)
    return R, np.array([0, 1.0, 0]) + R @ np.array([0, 0.5, 0])

def hazirla(t):
    p = egri(t)
    Rt, pt = govde(p)
    # bıçak ucunun hedefi: sağ omuzdan, istenen yöne, istenen yükseklikte (her zaman erişilebilir)
    om = pt + Rt @ OMUZ["R"]
    dy = float(np.clip(YER + p["yuk"] - om[1], -UC_UZAKLIK + 0.2, UC_UZAKLIK - 0.2))
    yat = math.sqrt(UC_UZAKLIK ** 2 - dy * dy)
    a = math.radians(p["yon"])
    p["uc"] = om + np.array([math.sin(a) * yat, dy, -math.cos(a) * yat])
    return p, Rt, pt

def uret():
    rng = np.random.default_rng(7)
    n = int(round(SURE * FPS))
    zamanlar = [i / FPS for i in range(n + 1)]
    zamanlar = sorted(set(round(t, 4) for t in zamanlar + [KES_T, SURE]))
    # Önce "Kes" karesini baştan çöz, sonra oradan geriye ve ileriye doğru sıcak başlat
    orta = zamanlar.index(round(KES_T, 4))
    cozum = {}
    p, Rt, pt = hazirla(zamanlar[orta])
    cozum[orta], _ = coz(Rt, pt, p, None, rng)
    for sira in (range(orta + 1, len(zamanlar)), range(orta - 1, -1, -1)):
        x = cozum[orta]
        for i in sira:
            p, Rt, pt = hazirla(zamanlar[i])
            x = X_DINLEN.copy() if p["dinlen"] > 0.999 else coz(Rt, pt, p, x, rng)[0]
            cozum[i] = x
    kareler, hata = [], []
    for i, t in enumerate(zamanlar):
        p, Rt, pt = hazirla(t)
        x = cozum[i]
        RR, RL, elR, elL, kok, uc = kol_durum(x)
        if p["dinlen"] < 0.05:
            hata.append(float(np.linalg.norm(elL - kol_noktasi(RR, SOL_EL))))
        if abs(t - KES_T) < 1e-6 or abs(t - 0.8) < 0.01 or abs(t - 0.2667) < 0.01:
            asagi = -(Rt @ RR @ np.array([1.0, 0, 0]))[1]
            print("t=%.2f bıçak yatıklığı %.2f (1 = tam yatık), bıçak kökü yerden %.2f, ucu yerden %.2f, uç hatası %.2f" % (
                t, asagi, (pt + Rt @ kok)[1] - YER, (pt + Rt @ uc)[1] - YER, np.linalg.norm(pt + Rt @ uc - p["uc"])))
        Rh, ph = kafa(p, Rt, pt, pt + Rt @ uc)
        par = {"Torso": (Rt, pt), "Head": (Rh, ph),
               "Right Arm": (RR, OMUZ["R"] + RR @ KOL_MERKEZ["R"]), "Left Arm": (RL, OMUZ["L"] + RL @ KOL_MERKEZ["L"])}
        for taraf, ad in (("R", "Right Leg"), ("L", "Left Leg")):
            Rb, pb = bacak(p, Rt, pt, taraf)
            par[ad] = (Rt.T @ Rb, Rt.T @ (pb - pt))          # gövde uzayına çevir
        kareler.append((t, par))
    print("sol el - hedef arası en büyük boşluk: %.3f stud (ortalama %.3f)" % (max(hata), sum(hata) / len(hata)))
    return kareler

# ---------------- Roblox eklem uzayına çevirme ----------------
r_kok = np.array([[-1, 0, 0], [0, 0, 1], [0, 1, 0.0]])
r_R = np.array([[0, 0, 1], [0, 1, 0], [-1, 0, 0.0]])
r_L = np.array([[0, 0, -1], [0, 1, 0], [1, 0, 0.0]])
EKLEM = {  # parça: (C0 konum, C1 konum, dönüş)
    "Torso": ((0, 0, 0), (0, 0, 0), r_kok), "Head": ((0, 1, 0), (0, -0.5, 0), r_kok),
    "Right Arm": ((1, 0.5, 0), (-0.5, 0.5, 0), r_R), "Left Arm": ((-1, 0.5, 0), (0.5, 0.5, 0), r_L),
    "Right Leg": ((1, -1, 0), (0.5, 1, 0), r_R), "Left Leg": ((-1, -1, 0), (-0.5, 1, 0), r_L),
}
SIRA = ["Torso", "Head", "Right Arm", "Left Arm", "Right Leg", "Left Leg"]
def donusum(ad, R, p):
    """Transform = C0^-1 * D * C1"""
    c0, c1, r = EKLEM[ad]
    Rn = r.T @ R @ r
    pn = r.T @ (p + R @ np.array(c1, float) - np.array(c0, float))
    return pn, quat(Rn)

LUA_BAS = '''--[[
	TIRPANLA SAMAN BİÇME — R6 animasyon oluşturucu  (otomatik üretildi: roblox/tools/tirpan_uret.py)
	----------------------------------------------------------------------------------------------
	Nasıl kullanılır:
	  1. Roblox Studio'da View > Command Bar'ı aç.
	  2. Bu dosyanın tamamını kopyalayıp Command Bar'a yapıştır, Enter'a bas.
	  3. ServerStorage > RBX_ANIMSAVES > Rig altında "TirpanBicme" oluşur.
	  4. Avatar > Rig Builder ile bir R6 rig ekle (adı "Rig" olsun), Animation Editor'ı aç,
	     rig'i seç, "..." menüsünden "Load" ile TirpanBicme'yi yükle.
	  5. "..." > "Publish to Roblox" ile yükle ve çıkan ID'yi TirpanSalla script'ine yaz.

	Hareket: oyundaki tırpan tutuşundan (sağ kol önde) başlar > tırpan sağ geriye çekilir > belden eğilip
	tek diz üstüne çökerek sağdan sola savrulur ("Kes" anı) > kalkıp baştaki tutuşa döner.
	Sol el, sağ elin hemen yanında durur.
	Tırpanın eldeki yeri oyundaki "normal tırpan" Tool'undan ölçüldü (Grip değiştirilmedi): sap kola dik,
	yana doğru uzanır; bıçak kolun uzandığı yöne bakar.
	Pozlar hesapla üretildiği için burada elle düzenlenmez; hareketi değiştirmek için üreticideki
	ANAHTAR tablosu düzenlenip dosya yeniden üretilir.
]]

local ServerStorage = game:GetService("ServerStorage")
local ANIM_ADI = "TirpanBicme"
local RIG_ADI = "Rig"
local PARCALAR = { "Torso", "Head", "Right Arm", "Left Arm", "Right Leg", "Left Leg" }

-- Her satır: zaman, ad, sonra 6 parça x (x, y, z, qX, qY, qZ, qW)
local KARELER = {
'''
LUA_SON = '''}

local seq = Instance.new("KeyframeSequence")
seq.Name = ANIM_ADI
seq.Loop = false
seq.Priority = Enum.AnimationPriority.Action

local function pozEkle(ust, ad, cf)
	local pose = Instance.new("Pose")
	pose.Name = ad
	pose.CFrame = cf
	pose.EasingStyle = Enum.PoseEasingStyle.Linear
	pose.EasingDirection = Enum.PoseEasingDirection.In
	pose.Parent = ust
	return pose
end

for _, k in ipairs(KARELER) do
	local kf = Instance.new("Keyframe")
	kf.Time = k[1]
	kf.Name = k[2] ~= "" and k[2] or "Keyframe"
	local kok = pozEkle(kf, "HumanoidRootPart", CFrame.identity)
	local torso
	for i, ad in ipairs(PARCALAR) do
		local o = 3 + (i - 1) * 7
		local cf = CFrame.new(k[o], k[o + 1], k[o + 2], k[o + 3], k[o + 4], k[o + 5], k[o + 6])
		if i == 1 then torso = pozEkle(kok, ad, cf) else pozEkle(torso, ad, cf) end
	end
	kf.Parent = seq
end

-- Animation Editor'ın "Load" listesinde görünmesi için RBX_ANIMSAVES'e koy
local saves = ServerStorage:FindFirstChild("RBX_ANIMSAVES")
if not saves then
	saves = Instance.new("Model")
	saves.Name = "RBX_ANIMSAVES"
	saves.Parent = ServerStorage
end
local rig = workspace:FindFirstChild(RIG_ADI)
local rigKlasoru = saves:FindFirstChild(RIG_ADI)
if not rigKlasoru then
	rigKlasoru = Instance.new("ObjectValue")
	rigKlasoru.Name = RIG_ADI
	rigKlasoru.Parent = saves
end
if rig then rigKlasoru.Value = rig end
local eski = rigKlasoru:FindFirstChild(ANIM_ADI)
if eski then eski:Destroy() end
seq.Parent = rigKlasoru

print(("✅ %s oluşturuldu (%d kare, %.1f sn). Animation Editor'da '%s' rig'ini seçip Load menüsünden açabilirsin.")
	:format(ANIM_ADI, #KARELER, KARELER[#KARELER][1], RIG_ADI))
'''

def f3(v): 
    s = "%.3f" % v
    s = s.rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s

def main():
    kareler = uret()
    adlar = {round(k["t"], 4): k["ad"] for k in ANAHTAR if k["ad"]}
    satirlar = []
    for t, par in kareler:
        s = [f3(t), '"%s"' % adlar.get(round(t, 4), "")]
        for ad in SIRA:
            pn, q = donusum(ad, *par[ad])
            s += [f3(v) for v in list(pn) + list(q)]
        satirlar.append("\t{" + ",".join(s) + "},")
    kok = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(kok, "TirpanAnimasyonu_Olustur.lua"), "w", encoding="utf-8") as f:
        f.write(LUA_BAS + "\n".join(satirlar) + "\n" + LUA_SON)
    print("Lua yazıldı: %d kare" % len(kareler))
    if len(sys.argv) > 1:
        veri = {"sure": SURE, "kes": KES_T, "sap": [SAP_Y, SAP_Z, SAP_YARI], "bicak": [BICAK_X, BICAK_BOY] + list(BICAK_YON),
                "adimlar": [[k["t"], k["ad"]] for k in ANAHTAR if k["ad"]],
                "kareler": [[round(t, 4)] + [round(float(v), 4) for ad in SIRA for v in list(par[ad][1]) + list(quat(par[ad][0]))] for t, par in kareler]}
        with open(sys.argv[1], "w", encoding="utf-8") as f: json.dump(veri, f, separators=(",", ":"))
        print("JSON yazıldı:", sys.argv[1])

if __name__ == "__main__":
    main()
