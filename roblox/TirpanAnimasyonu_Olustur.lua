--[[
	TIRPANLA SAMAN BİÇME — R6 animasyon oluşturucu
	----------------------------------------------
	Nasıl kullanılır:
	  1. Roblox Studio'da View > Command Bar'ı aç.
	  2. Bu dosyanın tamamını kopyalayıp Command Bar'a yapıştır, Enter'a bas.
	  3. ServerStorage > RBX_ANIMSAVES altında "TirpanBicme" oluşur.
	  4. Avatar > Rig Builder ile bir R6 rig ekle (adı "Rig" olsun), Animation Editor'ı aç,
	     rig'i seç, "..." menüsünden "Load" ile TirpanBicme'yi yükle.
	  5. Beğenince "..." > "Publish to Roblox" ile yükle ve çıkan ID'yi TirpanSalla script'ine (StarterPlayerScripts) yaz.

	Pozları değiştirmek için aşağıdaki ADIMLAR tablosunu düzenle (dereceler):
	  kol/bacak:  ileri (+ öne kaldır, - arkaya), disari (+ yana aç, - içeri / göğse çapraz)
	  govde:      egil (+ öne eğil), don (+ sağa dön), cok (kaç stud aşağı insin)
	  kafa:       egil (+ aşağı bak), don (+ sağa bak)
]]

local ServerStorage = game:GetService("ServerStorage")
local ANIM_ADI = "TirpanBicme"
local RIG_ADI = "Rig"

-- Standart R6 eklem (Motor6D) C0 dönüşleri
local C0 = {
	["Torso"]     = CFrame.new(0, 0, 0, -1, 0, 0, 0, 0, 1, 0, 1, 0),   -- RootJoint
	["Head"]      = CFrame.new(0, 0, 0, -1, 0, 0, 0, 0, 1, 0, 1, 0),   -- Neck
	["Right Arm"] = CFrame.new(0, 0, 0, 0, 0, 1, 0, 1, 0, -1, 0, 0),   -- Right Shoulder
	["Left Arm"]  = CFrame.new(0, 0, 0, 0, 0, -1, 0, 1, 0, 1, 0, 0),   -- Left Shoulder
	["Right Leg"] = CFrame.new(0, 0, 0, 0, 0, 1, 0, 1, 0, -1, 0, 0),   -- Right Hip
	["Left Leg"]  = CFrame.new(0, 0, 0, 0, 0, -1, 0, 1, 0, 1, 0, 0),   -- Left Hip
}

local rad = math.rad

-- Gövde-uzayındaki bir hareketi eklemin kendi uzayına çevirir
local function eklemUzayina(parca, cf)
	local r = C0[parca]
	return r:Inverse() * cf * r
end

local function uzuv(parca, p)
	p = p or {}
	local taraf = parca:find("Right") and 1 or -1
	local cf = CFrame.Angles(rad(p.ileri or 0), 0, taraf * rad(p.disari or 0))
	return eklemUzayina(parca, cf)
end

local function govde(p)
	p = p or {}
	local cf = CFrame.new(0, -(p.cok or 0), 0)
		* CFrame.Angles(-rad(p.egil or 0), -rad(p.don or 0), 0)
	return eklemUzayina("Torso", cf)
end

local function kafa(p)
	p = p or {}
	return eklemUzayina("Head", CFrame.Angles(-rad(p.egil or 0), -rad(p.don or 0), 0))
end

-- Videodaki hareketin adımları (zaman saniye cinsinden)
-- "stil": bu pozdan bir SONRAKİ poza geçişin yumuşaklığı (Cubic, Linear, Bounce, Elastic, Constant)
local ADIMLAR = {
	{ t = 0.0, ad = "Hazir",
		govde = {}, kafa = {},
		sagKol = { ileri = 40 }, solKol = { ileri = 45, disari = -30 } },
	{ t = 0.35, ad = "Kaldir", stil = "Linear",        -- tırpan sağ omzun üstünde, geriye kaldırılmış
		govde = { don = 45, egil = -5 }, kafa = { don = -20 },
		sagKol = { ileri = 150, disari = 25 }, solKol = { ileri = 135, disari = -55 },
		sagBacak = { ileri = 10 }, solBacak = { ileri = -10 } },
	{ t = 0.6, ad = "Savur", stil = "Linear",           -- savurma ortası, alçalmaya başlıyor
		govde = { cok = 0.5, egil = 18, don = 5 },
		sagKol = { ileri = 80, disari = -10 }, solKol = { ileri = 75, disari = -30 },
		sagBacak = { ileri = 30 }, solBacak = { ileri = -30 } },
	{ t = 0.85, ad = "Kes",                             -- tek diz yerde, tırpan sol altta: saman kesildi
		govde = { cok = 1.2, egil = 25, don = -35 }, kafa = { egil = 10, don = -10 },
		sagKol = { ileri = 55, disari = -45 }, solKol = { ileri = 50, disari = 10 },
		sagBacak = { ileri = 65 }, solBacak = { ileri = -65 } },
	{ t = 1.6, ad = "Bekle",
		govde = { cok = 1.15, egil = 22, don = -30 }, kafa = { egil = 8, don = -10 },
		sagKol = { ileri = 55, disari = -40 }, solKol = { ileri = 50, disari = 10 },
		sagBacak = { ileri = 65 }, solBacak = { ileri = -65 } },
	{ t = 2.1, ad = "Kalk",
		govde = { cok = 0.6, egil = 25, don = -10 }, kafa = { egil = 5 },
		sagKol = { ileri = 50, disari = -15 }, solKol = { ileri = 50, disari = -10 },
		sagBacak = { ileri = 30 }, solBacak = { ileri = -30 } },
	{ t = 2.5, ad = "Dogrul",
		govde = { cok = 0.1, egil = 5, don = 10 },
		sagKol = { ileri = 70, disari = 5 }, solKol = { ileri = 75, disari = -40 } },
	{ t = 2.85, ad = "OmzaAl",                          -- tırpanı başın sağ yanına kaldır
		govde = { don = 15 }, kafa = { egil = -5, don = 5 },
		sagKol = { ileri = 155, disari = 10 }, solKol = { ileri = 145, disari = -45 } },
	{ t = 3.3, ad = "Omuzda",                           -- tırpan sağ omuzda dinleniyor
		govde = { don = 10 },
		sagKol = { ileri = 85, disari = 20 }, solKol = { ileri = 90, disari = -55 } },
	{ t = 3.9, ad = "Omuzda2",
		govde = { don = 10 },
		sagKol = { ileri = 85, disari = 20 }, solKol = { ileri = 90, disari = -55 } },
	{ t = 4.3, ad = "Bitis",                            -- başlangıç duruşuna dön (tekrar biçmeye hazır)
		govde = {}, kafa = {},
		sagKol = { ileri = 40 }, solKol = { ileri = 45, disari = -30 } },
}

-- KeyframeSequence oluştur
local seq = Instance.new("KeyframeSequence")
seq.Name = ANIM_ADI
seq.Loop = false
seq.Priority = Enum.AnimationPriority.Action

local function pozEkle(ust, parcaAdi, cf, stil)
	local pose = Instance.new("Pose")
	pose.Name = parcaAdi
	pose.CFrame = cf
	pose.EasingStyle = Enum.PoseEasingStyle[stil or "Cubic"]
	pose.EasingDirection = Enum.PoseEasingDirection.InOut
	pose.Parent = ust
	return pose
end

for _, a in ipairs(ADIMLAR) do
	local kf = Instance.new("Keyframe")
	kf.Name = a.ad
	kf.Time = a.t
	local kok = pozEkle(kf, "HumanoidRootPart", CFrame.identity, a.stil)
	local torso = pozEkle(kok, "Torso", govde(a.govde), a.stil)
	pozEkle(torso, "Head", kafa(a.kafa), a.stil)
	pozEkle(torso, "Right Arm", uzuv("Right Arm", a.sagKol), a.stil)
	pozEkle(torso, "Left Arm", uzuv("Left Arm", a.solKol), a.stil)
	pozEkle(torso, "Right Leg", uzuv("Right Leg", a.sagBacak), a.stil)
	pozEkle(torso, "Left Leg", uzuv("Left Leg", a.solBacak), a.stil)
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

print(("✅ %s oluşturuldu (%d adım). Animation Editor'da '%s' rig'ini seçip Load menüsünden açabilirsin.")
	:format(ANIM_ADI, #ADIMLAR, RIG_ADI))
