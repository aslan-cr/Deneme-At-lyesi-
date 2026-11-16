#!/usr/bin/env python3
"""
Tırpan biçme animasyonu üretici (R6).

Hareketi üst seviye eğrilerle tanımlar (eğilme, çökme, sağ kolun yönü ve kendi ekseninde dönüşü),
her kare için bacakları ayaklar yerde kalacak şekilde yerleştirir ve pozları Roblox eklem
uzayına çevirir.
Çıktı:  roblox/TirpanAnimasyonu_Olustur.lua  ve (istenirse) önizleme için JSON.

Kullanım:  python3 roblox/tools/tirpan_uret.py [onizleme.json]

Tırpanın eldeki yeri oyundaki "dırpan" Tool'undan ölçüldü (Grip = CFrame(0,-0.2,0) * Y'de -90°,
standart RightGrip): sap avucun içinden geçer ve kol aşağı sarkarken öne (kolun yerel -Z yönü)
uzanır; bıçak sapın ucundan kolun +Y yönüne (omuza doğru) çıkar. Bu yüzden kol yana açıkken
bıçak gövdenin önünde, yere paralel ve sola bakar; kol omuzdan döndükçe bıçak bir yay çizer.
Gövde sağa sola dönmez; savuruşu yalnızca sağ kol yapar (tek elle).
"""
import json, math, os, sys
import numpy as np

FPS = 30
SURE = 1.6
KES_T = 0.5
# --- Tırpanın sağ kol uzayındaki yeri (omuz eklemine göre; kol merkezi (0.5,-0.5,0)) ---
SAP_UCU = np.array([0.5, -1.5, -3.4])     # sapın uzak ucu = bıçağın kökü (el: (0.5,-1.5,0))
SAP_ARKA = np.array([0.5, -1.5, 0.55])    # sapın elin arkasında kalan ucu
BICAK = np.array([0, 2.24, 0])            # bıçak kökünden ucuna (kolun +Y yönü)
# Oyunda tırpan eldeyken beklerken ölçülen sol kol dönüşü (Torso'ya göre)
SOL_BEKLEME = np.array([[0.5887, -0.6955, 0.4120], [-0.7696, -0.3263, 0.5489], [-0.2473, -0.6402, -0.7273]])
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
def donme_vektoru(R):
    q = quat(R); v = q[:3]; n = np.linalg.norm(v)
    return np.zeros(3) if n < 1e-9 else v / n * 2 * math.atan2(n, q[3])
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
# egil: öne eğilme, yan: sola yatma, cok: kalça alçalması, geri: kalçanın geriye kayması,
# diz: tek diz çökme (0-1), dinlen: oyundaki bekleme duruşuna yakınlık (1 = baş dümdüz ileri bakar),
# Sağ kol (dünya yönleriyle, gövdenin eğilmesinden bağımsız):
#   kyon: kolun baktığı yön (0 = ileri, 90 = sağ, 180 = arka)
#   kkalk: kolun kalkışı (0 = aşağı sarkık, 90 = yatay, 180 = dümdüz yukarı)
#   kdon: kolun kendi ekseni etrafında dönüşü; tırpanı elde çeviren budur
#         (kol yatayken: 90 = sap kolun solunda yatay, 180 = sap dümdüz aşağı)
# yerde (0-1) / yuk: yerde = 1 iken kdon elle verilen değer yerine, bıçağın en alt noktası yerden tam
#   "yuk" stud yukarıda kalacak şekilde her karede yeniden hesaplanır (bıçak yere yakın ama yere girmez)
# Bıçağın bulunduğu yön = kyon - 90 (kol sağa bakarken bıçak tam önde).
# İlk ve son satır aynı duruştur (oyunda ölçülen bekleme: kol yukarıda, 18° arkaya yatık); kol dikken
# kyon ile kdon birbirinin yerine geçtiği için başta "arkadan in", sonda "önden kalk" diye iki ayrı yazılır.
# sol / solyan: sol kolun öne ve yana açılması (derece)
ANAHTAR = [
    dict(t=0.00, ad="Bel",    dur=1, egil=0,  yan=0, cok=0.00, geri=0.0,  diz=0,   dinlen=1, kyon=180, kkalk=162, kdon=180, yerde=0, yuk=0.5,  sol=0,  solyan=0),
    dict(t=0.30, ad="Geri",   dur=0, egil=18, yan=0, cok=0.50, geri=0.1,  diz=0.3, dinlen=0, kyon=165, kkalk=100, kdon=118, yerde=0, yuk=0.5,  sol=30, solyan=14),
    dict(t=0.42, ad="Savur",  dur=0, egil=40, yan=3, cok=1.00, geri=0.0,  diz=0.9, dinlen=0, kyon=135, kkalk=84,  kdon=122, yerde=1, yuk=0.45, sol=22, solyan=18),
    dict(t=0.50, ad="Kes",    dur=0, egil=50, yan=4, cok=1.20, geri=-0.1, diz=1,   dinlen=0, kyon=90,  kkalk=80,  kdon=117, yerde=1, yuk=0.25, sol=5,  solyan=20),
    dict(t=0.64, ad="",       dur=0, egil=52, yan=5, cok=1.22, geri=-0.1, diz=1,   dinlen=0, kyon=42,  kkalk=80,  kdon=117, yerde=1, yuk=0.25, sol=-18, solyan=20),
    dict(t=0.80, ad="Bekle",  dur=1, egil=48, yan=4, cok=1.18, geri=-0.1, diz=1,   dinlen=0, kyon=33,  kkalk=80,  kdon=117, yerde=1, yuk=0.3,  sol=-22, solyan=18),
    dict(t=1.00, ad="",       dur=1, egil=46, yan=3, cok=1.15, geri=-0.1, diz=1,   dinlen=0, kyon=35,  kkalk=81,  kdon=117, yerde=1, yuk=0.35, sol=-20, solyan=16),
    dict(t=1.30, ad="Kalk",   dur=0, egil=12, yan=0, cok=0.30, geri=0.0,  diz=0.2, dinlen=0.5, kyon=30, kkalk=150, kdon=40, yerde=0, yuk=0.5,  sol=-5, solyan=6),
    dict(t=1.60, ad="Bitis",  dur=1, egil=0,  yan=0, cok=0.00, geri=0.0,  diz=0,   dinlen=1, kyon=0,   kkalk=198, kdon=0,   yerde=0, yuk=0.5,  sol=0,  solyan=0),
]
ALANLAR = ["egil", "yan", "cok", "geri", "diz", "dinlen", "kyon", "kkalk", "kdon", "yerde", "yuk", "sol", "solyan"]

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
    d["diz"] = min(max(d["diz"], 0), 1); d["don"] = 0.0; d["yerde"] = min(max(d["yerde"], 0), 1)
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

def kollar(p, Rt):
    """Sağ ve sol kolun gövde uzayındaki dönüşleri."""
    Rw = Ry(-math.radians(p["kyon"])) @ Rx(math.radians(p["kkalk"])) @ Ry(math.radians(p["kdon"]))
    RL = Rx(math.radians(p["sol"])) @ Rz(-math.radians(p["solyan"]))
    RL = rodrigues(p["dinlen"] * donme_vektoru(SOL_BEKLEME @ RL.T)) @ RL     # beklerken oyundaki sol kol duruşu
    return Rt.T @ Rw, RL

BICAK_EN = 0.4   # bıçağın sap doğrultusundaki yarı genişliği
def bicak_alt(p, Rt, pt):
    """Bıçağın en alt köşesinin yerden yüksekliği."""
    RR = kollar(p, Rt)[0]
    kok = OMUZ["R"] + RR @ SAP_UCU
    return min((pt + Rt @ (kok + RR @ (BICAK * a + np.array([0, 0, b]))))[1] for a in (0, 1) for b in (-BICAK_EN, BICAK_EN)) - YER

def yere_oturt(p, Rt, pt):
    """yerde > 0 ise kdon'u, bıçağın en alt noktası 'yuk' yüksekliğine gelecek şekilde ayarlar."""
    if p["yerde"] <= 0: return
    alt, ust = 90.0, 175.0                     # bu aralıkta kdon büyüdükçe bıçak alçalır
    for _ in range(40):
        orta = (alt + ust) / 2
        if bicak_alt(dict(p, kdon=orta), Rt, pt) > p["yuk"]: alt = orta
        else: ust = orta
    p["kdon"] += p["yerde"] * ((alt + ust) / 2 - p["kdon"])

def tirpan(RR):
    """Sapın arka ucu, bıçak kökü ve bıçak ucu (gövde uzayında)."""
    arka = OMUZ["R"] + RR @ SAP_ARKA
    kok = OMUZ["R"] + RR @ SAP_UCU
    return arka, kok, kok + RR @ BICAK

def kutuya_uzaklik(q, merkez, yari):
    d = np.maximum(np.abs(q - merkez) - yari, 0)
    return float(np.linalg.norm(d))

def kafa(p, Rt, pt, uc_dunya):
    bas = pt + Rt @ np.array([0, 1.5, 0])
    hedef = norm(0.45 * np.array([0, -0.15, -1.0]) + 0.55 * norm(uc_dunya - bas))
    v = Rt.T @ hedef
    w = 1 - p["dinlen"]
    yaw = w * float(np.clip(math.atan2(-v[0], -v[2]), -1.2, 1.2))
    pitch = w * float(np.clip(math.asin(np.clip(v[1], -1, 1)), -0.6, 0.5))
    R = Ry(yaw) @ Rx(pitch)
    return R, np.array([0, 1.0, 0]) + R @ np.array([0, 0.5, 0])

def uret():
    n = int(round(SURE * FPS))
    zamanlar = [i / FPS for i in range(n + 1)]
    zamanlar = sorted(set(round(t, 4) for t in zamanlar + [KES_T, SURE]))
    kareler, en_yakin = [], (9.0, 0.0)
    anahtar_t = {round(k["t"], 4): k["ad"] for k in ANAHTAR}
    for t in zamanlar:
        p = egri(t)
        Rt, pt = govde(p)
        yere_oturt(p, Rt, pt)
        RR, RL = kollar(p, Rt)
        arka, kok, uc = tirpan(RR)
        dunya = lambda q: pt + Rt @ q
        # tırpan gövdeye / kafaya ne kadar yaklaşıyor, yere giriyor mu
        ornek = [arka + (kok - arka) * k for k in np.linspace(0.25, 1, 7)] + [kok + (uc - kok) * k for k in (0.33, 0.66, 1.0)]
        yakin = min(min(kutuya_uzaklik(q, np.zeros(3), np.array([1.0, 1.0, 0.5])),
                        kutuya_uzaklik(q, np.array([0, 1.5, 0]), np.array([0.6, 0.5, 0.5]))) for q in ornek)
        if yakin < en_yakin[0]: en_yakin = (yakin, t)
        if t in anahtar_t:
            b = Rt @ RR @ np.array([0, 1.0, 0])
            yatik = abs((Rt @ RR @ np.array([1.0, 0, 0]))[1])
            print("t=%.2f %-6s bıçağın en altı yerden %5.2f, yatıklığı %.2f (1 = tam yatık), yönü %4.0f° (0 ileri, - sol), gövdeye uzaklık %.2f" % (
                t, anahtar_t[t], bicak_alt(p, Rt, pt), yatik, math.degrees(math.atan2(b[0], -b[2])), yakin))
        Rh, ph = kafa(p, Rt, pt, dunya(uc))
        par = {"Torso": (Rt, pt), "Head": (Rh, ph),
               "Right Arm": (RR, OMUZ["R"] + RR @ KOL_MERKEZ["R"]), "Left Arm": (RL, OMUZ["L"] + RL @ KOL_MERKEZ["L"])}
        for taraf, ad in (("R", "Right Leg"), ("L", "Left Leg")):
            Rb, pb = bacak(p, Rt, pt, taraf)
            par[ad] = (Rt.T @ Rb, Rt.T @ (pb - pt))          # gövde uzayına çevir
        kareler.append((t, par))
    print("tırpanın gövdeye/kafaya en yakın olduğu an: t=%.2f, %.2f stud" % (en_yakin[1], en_yakin[0]))
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

	Hareket: tırpan omuzda (sağ kol yukarıda) başlar > kol inerken tırpan elde dönüp sağ geriye gelir >
	öne eğilip tek diz üstüne çökerek, bıçak yere yakın ve sola bakarken sağdan sola savrulur
	("Kes" anı) > kalkıp tırpan yeniden omuza alınır. Gövde sağa sola dönmez; savuruş tek elle yapılır.
	Tırpanın eldeki yeri oyundaki "dırpan" Tool'undan ölçüldü: sap avucun içinden geçip kola dik uzanır,
	bıçak sapın ucundadır.
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
        veri = {"sure": SURE, "kes": KES_T, "sapArka": list(SAP_ARKA), "sapUcu": list(SAP_UCU), "bicak": list(BICAK),
                "adimlar": [[k["t"], k["ad"]] for k in ANAHTAR if k["ad"]],
                "kareler": [[round(t, 4)] + [round(float(v), 4) for ad in SIRA for v in list(par[ad][1]) + list(quat(par[ad][0]))] for t, par in kareler]}
        with open(sys.argv[1], "w", encoding="utf-8") as f: json.dump(veri, f, separators=(",", ":"))
        print("JSON yazıldı:", sys.argv[1])

if __name__ == "__main__":
    main()
