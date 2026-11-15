--[[
	DIZ ÇÖKME DANSI — R6 animasyon oluşturucu
	-----------------------------------------
	Nasıl kullanılır:
	  1. Roblox Studio'da View > Command Bar'ı aç.
	  2. Bu dosyanın tamamını kopyalayıp Command Bar'a yapıştır, Enter'a bas.
	  3. ServerStorage > RBX_ANIMSAVES altında "DizCokmeDansi" oluşur.
	  4. Avatar > Rig Builder ile bir R6 rig ekle (adı "Rig" olsun), Animation Editor'ı aç,
	     rig'i seç, "..." menüsünden "Load" ile DizCokmeDansi'yı yükle.
	  5. Beğenince "..." > "Publish to Roblox" ile yükle ve çıkan ID'yi DansTusu script'ine yaz.

	Pozları değiştirmek için aşağıdaki ADIMLAR tablosunu düzenle (dereceler):
	  kol/bacak:  ileri (+ öne kaldır, - arkaya), disari (+ yana aç, - içeri / göğse çapraz)
	  govde:      egil (+ öne eğil), don (+ sağa dön), cok (kaç stud aşağı insin)
	  kafa:       egil (+ aşağı bak), don (+ sağa bak)
]]

local ServerStorage = game:GetService("ServerStorage")
local ANIM_ADI = "DizCokmeDansi"
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
local ADIMLAR = {
	{ t = 0.0, ad = "Basla",
		govde = {}, kafa = {} },
	{ t = 0.4, ad = "Hazirlik",          -- yana dön, sağ kolu geri çek
		govde = { don = 35, egil = 5 }, kafa = { don = -25 },
		sagKol = { ileri = -45, disari = 20 }, solKol = { ileri = 40, disari = -20 } },
	{ t = 0.8, ad = "Inis",
		govde = { cok = 0.5, egil = 15, don = 15 }, kafa = { don = -10 },
		sagKol = { ileri = -20, disari = 15 }, solKol = { ileri = 20 },
		sagBacak = { ileri = 30 }, solBacak = { ileri = -30 } },
	{ t = 1.05, ad = "DizCok_Yumruk", stil = "Bounce",   -- tek diz yere, sağ yumruk öne
		govde = { cok = 1.2, egil = 15 }, kafa = { egil = -5 },
		sagKol = { ileri = 90 }, solKol = { ileri = -25, disari = 15 },
		sagBacak = { ileri = 65 }, solBacak = { ileri = -65 } },
	{ t = 1.8, ad = "DizCok_Bekle",
		govde = { cok = 1.15, egil = 18 }, kafa = { egil = -8 },
		sagKol = { ileri = 85 }, solKol = { ileri = -25, disari = 15 },
		sagBacak = { ileri = 65 }, solBacak = { ileri = -65 } },
	{ t = 2.3, ad = "Kalkis",
		govde = { cok = 0.6, egil = 25, don = -10 }, kafa = { egil = 5 },
		sagKol = { ileri = 35 }, solKol = { ileri = 20 },
		sagBacak = { ileri = 30 }, solBacak = { ileri = -30 } },
	{ t = 2.7, ad = "Dogrul",
		govde = { cok = 0.1, egil = 8, don = -20 }, kafa = { don = 10 },
		sagKol = { ileri = 45, disari = -20 }, solKol = { ileri = 30, disari = -10 } },
	{ t = 3.0, ad = "KollarGogse",
		govde = { don = -10 },
		sagKol = { ileri = 80, disari = -35 }, solKol = { ileri = 80, disari = -35 } },
	{ t = 3.3, ad = "SagKolYukari",
		govde = { don = 10 }, kafa = { egil = -10 },
		sagKol = { ileri = 165, disari = -10 }, solKol = { ileri = 70, disari = -35 } },
	{ t = 3.6, ad = "SolKolYukari",
		govde = { don = -10 }, kafa = { egil = -10 },
		sagKol = { ileri = 70, disari = -35 }, solKol = { ileri = 165, disari = -10 } },
	{ t = 3.9, ad = "KollarGogse2",
		sagKol = { ileri = 80, disari = -35 }, solKol = { ileri = 80, disari = -35 } },
	{ t = 4.4, ad = "Bitis",                -- kameraya dönüp dur
		govde = {}, kafa = {},
		sagKol = { disari = 8 }, solKol = { disari = 8 } },
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
