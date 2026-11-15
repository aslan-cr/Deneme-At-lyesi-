#!/usr/bin/env python3
"""
Tırpan biçme animasyonu üretici (R6).

Hareketi üst seviye eğrilerle tanımlar (gövde dönüşü, eğilme, çökme, tırpan ucunun
gideceği yer), sonra her kare için:
  - bacakları ayaklar yerde kalacak şekilde yerleştirir,
  - iki elin de tırpan sapını tutacağı kol açılarını çözer.
Çıktı:  roblox/TirpanAnimasyonu_Olustur.lua  ve (istenirse) önizleme için JSON.

Kullanım:  python3 roblox/tools/tirpan_uret.py [onizleme.json]
Varsayım: tırpan sağ ele standart Tool tutuşuyla bağlı; sap, sağ kolun yerel -Z
yönünde (kola dik) uzanır.
"""
import json, math, os, sys
import numpy as np

FPS = 30
SURE = 3.4
KES_T = 0.76
LF, LB = 3.2, 2.4        # sağ elden bıçak ucuna / sapın arka ucuna uzunluk
TUTUS = -1.9             # sol elin sap üzerindeki yeri (sağ ele göre)
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
# yon: tırpan sapının baktığı yön (0 = ileri, + = sağ, 180 = arka), yuk: sap ucunun yerden yüksekliği,
# duz: bıçağın yere paralel olma isteği (0-1)
ANAHTAR = [
    dict(t=0.00, ad="Hazir",  dur=1, don=10,  egil=12, yan=0,  cok=0.15, geri=0.0,  diz=0,   yon=70,  yuk=1.3,  duz=0.2),
    dict(t=0.45, ad="Kaldir", dur=1, don=62,  egil=-6, yan=-4, cok=0.10, geri=0.25, diz=0,   yon=150, yuk=6.0,  duz=0),
    dict(t=0.55, ad="",       dur=0, don=58,  egil=-2, yan=-3, cok=0.15, geri=0.2,  diz=0,   yon=140, yuk=5.5,  duz=0),
    dict(t=0.68, ad="Savur",  dur=0, don=15,  egil=28, yan=4,  cok=0.75, geri=0.0,  diz=0.7, yon=88,  yuk=0.6,  duz=1),
    dict(t=0.76, ad="Kes",    dur=0, don=-25, egil=38, yan=6,  cok=1.00, geri=-0.1, diz=1,   yon=42,  yuk=0.35, duz=1),
    dict(t=0.90, ad="",       dur=0, don=-75, egil=41, yan=8,  cok=1.08, geri=-0.1, diz=1,   yon=-15, yuk=0.35, duz=1),
    dict(t=1.05, ad="Bekle",  dur=1, don=-68, egil=37, yan=6,  cok=1.05, geri=-0.1, diz=1,   yon=-8,  yuk=0.4,  duz=1),
    dict(t=1.45, ad="",       dur=1, don=-65, egil=35, yan=5,  cok=1.02, geri=-0.1, diz=1,   yon=-5,  yuk=0.45, duz=1),
    dict(t=2.00, ad="Kalk",   dur=0, don=-10, egil=14, yan=0,  cok=0.18, geri=0.0,  diz=0,   yon=60,  yuk=1.7,  duz=0.2),
    dict(t=2.50, ad="Omuzda", dur=1, don=14,  egil=-3, yan=0,  cok=0.00, geri=0.0,  diz=0,   yon=145, yuk=6.3,  duz=0),
    dict(t=3.00, ad="",       dur=1, don=12,  egil=-1, yan=0,  cok=0.04, geri=0.0,  diz=0,   yon=143, yuk=6.25, duz=0),
    dict(t=3.40, ad="Bitis",  dur=1, don=10,  egil=12, yan=0,  cok=0.15, geri=0.0,  diz=0,   yon=70,  yuk=1.3,  duz=0.2),
]
ALANLAR = ["don", "egil", "yan", "cok", "geri", "diz", "duz", "yon", "yuk"]
BICAK_ACI = 0.15         # bıçak düzleminin sapa göre eğimi (radyan)

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

def kol_durum(Rt, pt, rR, rL):
    RR, RL = rodrigues(rR), rodrigues(rL)
    elR = OMUZ["R"] + RR @ EL["R"]; elL = OMUZ["L"] + RL @ EL["L"]
    s = RR @ np.array([0, 0, -1.0])
    return RR, RL, elR, elL, s

def kutuda(pt, yari, pay):
    d = np.maximum(yari + pay - np.abs(pt), 0)
    return float(np.min(d)) if np.all(d > 0) else 0.0

def maliyet(x, Rt, pt, p, onceki):
    RR, RL, elR, elL, s = kol_durum(Rt, pt, x[:3], x[3:])
    uc_g = Rt.T @ (p["uc"] - pt)                         # hedef, gövde uzayında
    uc = elR + s * LF
    e = 1.0 * np.sum((uc - uc_g) ** 2)
    # sol el sapın üstünde olsun
    lam = float(np.clip((elL - elR) @ s, TUTUS - 0.5, TUTUS + 0.6))
    e += 14.0 * np.sum((elL - (elR + s * lam)) ** 2)
    e += 0.4 * ((RL @ np.array([0, 1.0, 0])) @ s) ** 2   # sol kol sapa dik
    # bıçak yere paralel
    if p["duz"] > 0:
        n = Rt @ RR @ norm(np.array([0, math.cos(BICAK_ACI), math.sin(BICAK_ACI)]))
        e += 5.0 * p["duz"] * (1 - n[1])
    # çarpışmalar: eller ve sap gövdenin / kafanın içinden geçmesin
    for el in (elR, elL):
        e += 30 * kutuda(el, np.array([1.0, 1.0, 0.5]), 0.45) ** 2
    for lm in np.linspace(-LB, LF, 9):
        q = elR + s * lm
        e += 12 * kutuda(q, np.array([1.0, 1.0, 0.5]), 0.2) ** 2
        e += 12 * max(0.85 - np.linalg.norm(q - np.array([0, 1.6, 0])), 0) ** 2
        yer = (pt + Rt @ q)[1] - (YER + 0.1)
        e += 6 * min(yer, 0) ** 2                         # sap yere girmesin
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
    yaw = float(np.clip(math.atan2(-v[0], -v[2]), -1.2, 1.2))
    pitch = float(np.clip(math.asin(np.clip(v[1], -1, 1)), -0.6, 0.5))
    R = Ry(yaw) @ Rx(pitch)
    return R, np.array([0, 1.0, 0]) + R @ np.array([0, 0.5, 0])

def uret():
    rng = np.random.default_rng(7)
    n = int(round(SURE * FPS))
    zamanlar = [i / FPS for i in range(n + 1)]
    zamanlar = sorted(set(round(t, 4) for t in zamanlar + [KES_T, SURE]))
    # Döngü tutarlılığı için: önce t=0 çöz, sonra ileri doğru sıcak başlat
    kareler, x = [], None
    hata = []
    for t in zamanlar:
        p = egri(t)
        Rt, pt = govde(p)
        # sap ucunun hedefi: sağ omuzdan, istenen yöne, istenen yükseklikte (her zaman erişilebilir)
        om = pt + Rt @ OMUZ["R"]
        r_uc = math.sqrt(0.25 + 2.25 + LF * LF)
        dy = float(np.clip(YER + p["yuk"] - om[1], -r_uc + 0.2, r_uc - 0.2))
        yat = math.sqrt(r_uc * r_uc - dy * dy)
        a = math.radians(p["yon"])
        p["uc"] = om + np.array([math.sin(a) * yat, dy, -math.cos(a) * yat])
        x, fx = coz(Rt, pt, p, x, rng)
        RR, RL, elR, elL, s = kol_durum(Rt, pt, x[:3], x[3:])
        lam = float(np.clip((elL - elR) @ s, TUTUS - 0.5, TUTUS + 0.6))
        hata.append(float(np.linalg.norm(elL - (elR + s * lam))))
        if abs(t - KES_T) < 1e-6 or abs(t - 1.0667) < 0.02:
            nn = Rt @ RR @ norm(np.array([0, math.cos(BICAK_ACI), math.sin(BICAK_ACI)]))
            print("t=%.2f bıçak düzlüğü %.2f, uç hatası %.2f" % (t, nn[1], np.linalg.norm(pt + Rt @ (elR + s * LF) - p["uc"])))
        Rh, ph = kafa(p, Rt, pt, pt + Rt @ (elR + s * LF))
        par = {"Torso": (Rt, pt), "Head": (Rh, ph),
               "Right Arm": (RR, OMUZ["R"] + RR @ KOL_MERKEZ["R"]), "Left Arm": (RL, OMUZ["L"] + RL @ KOL_MERKEZ["L"])}
        for taraf, ad in (("R", "Right Leg"), ("L", "Left Leg")):
            Rb, pb = bacak(p, Rt, pt, taraf)
            par[ad] = (Rt.T @ Rb, Rt.T @ (pb - pt))          # gövde uzayına çevir
        kareler.append((t, par))
    print("sol el - sap arası en büyük boşluk: %.3f stud (ortalama %.3f)" % (max(hata), sum(hata) / len(hata)))
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

	Hareket: tırpanı sağ omzun üstüne kaldır > belden eğilip tek diz üstüne çökerek sağdan sola savur
	("Kes" anı) > kalk > tırpanı omza al > hazır duruşa dön. İki el de tırpanın sapını tutar.
	Varsayım: tırpan sağ ele standart Tool tutuşuyla bağlı (sap, kola dik olarak öne uzanır).
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
        veri = {"sure": SURE, "kes": KES_T, "lf": LF, "lb": LB, "bicakAci": BICAK_ACI,
                "adimlar": [[k["t"], k["ad"]] for k in ANAHTAR if k["ad"]],
                "kareler": [[round(t, 4)] + [round(float(v), 4) for ad in SIRA for v in list(par[ad][1]) + list(quat(par[ad][0]))] for t, par in kareler]}
        with open(sys.argv[1], "w", encoding="utf-8") as f: json.dump(veri, f, separators=(",", ":"))
        print("JSON yazıldı:", sys.argv[1])

if __name__ == "__main__":
    main()
