--[[
	TIRPAN ANİMASYONU — tırpan sallanınca (sol tık / dokunma) biçme animasyonunu oynatır.
	LocalScript: StarterPlayer > StarterPlayerScripts > TirpanAnimasyonu

	Saman kesmeyi de bu script başlatır: bıçak samana değince sunucuya CutHay gönderir
	(puanı, samanın gizlenip geri gelmesini ServerScriptService.Server yapar).

	Animasyonu "Publish to Roblox" ile yükledikten sonra çıkan sayıyı ANIM_ID'ye yaz.
]]

local ANIM_ID = "rbxassetid://0" -- <-- yayınlanan animasyonun ID'si buraya
local HIZ = 1                    -- 1 = normal hız; tırpanın SallamaSure'sine göre ayarlanır
local BITIS_GECIS = 0.3          -- saniye; vuruştan sonra kolun eski duruşa yumuşakça dönme süresi

local Players = game:GetService("Players")
local oyuncu = Players.LocalPlayer

local anim = Instance.new("Animation")
anim.AnimationId = ANIM_ID

local track

local function tirpanMi(alet)
	if not alet:IsA("Tool") then return false end
	if alet:GetAttribute("Tier") ~= nil then return true end
	local ad = alet.Name:lower()
	return ad:find("tırpan", 1, true) ~= nil or ad:find("tirpan", 1, true) ~= nil or ad:find("scythe", 1, true) ~= nil
end

local function karakterHazir(karakter)
	track = nil
	if ANIM_ID == "rbxassetid://0" then return end
	local humanoid = karakter:WaitForChild("Humanoid")
	local animator = humanoid:WaitForChild("Animator")
	track = animator:LoadAnimation(anim)
	track.Priority = Enum.AnimationPriority.Action
end

--[[
	SAMAN KESME — saman ancak tırpanın bıçağı ona DEĞDİĞİNDE kesilir.
	Animasyon oynarken her karede bıçağın etrafına bakılır; değdiği her samana
	(bir sallamada bir kez) sunucuya "kestim" denir. Sunucu da tırpanın gerçekten
	sallandığını, mesafeyi ve hızı kontrol eder (ServerScriptService.Server).
	Animasyon henüz yüklenmemişse (ANIM_ID = 0) bıçak hareket etmez; o zaman
	geçici olarak karakterin hemen önündeki tek saman kesilir.
]]
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")
local BICAK_PAYI = 1 -- stud; bıçağın çevresinde "değdi" sayılan ek pay

local cutHay
task.spawn(function()
	cutHay = ReplicatedStorage:WaitForChild("Remotes"):WaitForChild("CutHay")
end)

local function samanBul(parca)
	if parca:GetAttribute("Hay") == true then return parca end
	local ust = parca.Parent
	if ust and ust:IsA("BasePart") and ust:GetAttribute("Hay") == true then return ust end
	return nil
end

-- Bıçak = tırpanın, tutulan yerden (Handle) en uzaktaki parçası
local function bicakBul(alet)
	local handle = alet:FindFirstChild("Handle")
	if not handle then return nil end
	local enUzak, mesafe = nil, -1
	for _, p in ipairs(alet:GetDescendants()) do
		if p:IsA("BasePart") and p ~= handle then
			local m = (p.Position - handle.Position).Magnitude
			if m > mesafe then enUzak, mesafe = p, m end
		end
	end
	return enUzak or handle
end

local function kesmeTara(alet, sure)
	local karakter = oyuncu.Character
	local bicak = bicakBul(alet)
	if not karakter or not bicak or not cutHay then return end
	local ayar = OverlapParams.new()
	ayar.FilterType = Enum.RaycastFilterType.Exclude
	ayar.FilterDescendantsInstances = { karakter }
	local vurulan = {}
	local bitis = os.clock() + sure
	local baglanti
	baglanti = RunService.Heartbeat:Connect(function()
		if os.clock() > bitis or alet.Parent ~= karakter or not bicak.Parent then
			baglanti:Disconnect()
			return
		end
		local boyut = bicak.Size + Vector3.new(BICAK_PAYI, BICAK_PAYI, BICAK_PAYI) * 2
		for _, parca in ipairs(workspace:GetPartBoundsInBox(bicak.CFrame, boyut, ayar)) do
			local saman = samanBul(parca)
			if saman and not vurulan[saman] then
				vurulan[saman] = true
				cutHay:FireServer(saman)
			end
		end
	end)
end

-- Animasyon yokken geçici yedek: önündeki tek samanı kes (eski davranış)
local function onundekiniKes()
	local karakter = oyuncu.Character
	local kok = karakter and karakter:FindFirstChild("HumanoidRootPart")
	if not kok or not cutHay then return end
	local ayar = OverlapParams.new()
	ayar.FilterType = Enum.RaycastFilterType.Exclude
	ayar.FilterDescendantsInstances = { karakter }
	-- En yakın samanı seç (sunucu 10 stud'dan uzaktakini kabul etmez)
	local enYakin, enAz
	for _, parca in ipairs(workspace:GetPartBoundsInBox(kok.CFrame * CFrame.new(0, 0, -4), Vector3.new(8, 6, 8), ayar)) do
		local saman = samanBul(parca)
		if saman then
			local m = (saman.Position - kok.Position).Magnitude
			if not enAz or m < enAz then enYakin, enAz = saman, m end
		end
	end
	if enYakin then cutHay:FireServer(enYakin) end
end

local mesgul = false
local function salla(alet)
	if mesgul then return end
	if not track then
		-- Animasyon yok: tırpanın sallama süresi boyunca tekrar kesme yok
		mesgul = true
		task.delay(0.15, onundekiniKes) -- sunucu "sallanıyor" işaretini koysun diye kısa bekleme
		task.delay(alet:GetAttribute("SallamaSure") or 1, function() mesgul = false end)
		return
	end
	if track.IsPlaying then return end
	-- Animasyonu tırpanın sallama süresine sığdır (SallamaSure yoksa normal hız)
	local sure = alet:GetAttribute("SallamaSure")
	local hiz = HIZ
	if sure and sure > 0 and track.Length > 0 then
		hiz = track.Length / sure
	end
	track:Play(0.1, 1, hiz)
	-- Bitişte el bir anda eski yerine ışınlanmasın: sona doğru yumuşakça
	-- dururken duruşuna geri çek (kol tırpanı eski hâline çeker, uç yine aşağı döner)
	local sure2 = track.Length / hiz
	kesmeTara(alet, sure2) -- animasyon boyunca bıçak hangi samana değerse o kesilir
	local benimTrack = track
	task.delay(math.max(0, sure2 - BITIS_GECIS), function()
		if benimTrack.IsPlaying then benimTrack:Stop(BITIS_GECIS) end
	end)
end

local function aletBagla(alet)
	if not tirpanMi(alet) or alet:GetAttribute("AnimBagli") then return end
	alet:SetAttribute("AnimBagli", true)
	alet.Activated:Connect(function() salla(alet) end)
end

local function karakterBagla(karakter)
	task.spawn(karakterHazir, karakter)
	for _, c in ipairs(karakter:GetChildren()) do aletBagla(c) end
	karakter.ChildAdded:Connect(aletBagla)
end

if oyuncu.Character then karakterBagla(oyuncu.Character) end
oyuncu.CharacterAdded:Connect(karakterBagla)

--[[
	TIRPAN DÖNÜŞÜ — dururken tırpanın sivri ucu arkaya bakar. Sallanırken tırpan
	kendi sapı etrafında hızlıca döner, hilal kısmı öne (samanlara) bakarak vurur,
	sallama bitince yine hızlıca eski hâline döner. Karakter dönmez, sadece tırpan.
	Sunucu sallamada tırpana "swinging" işareti koyar (ScytheSwingSystem); bu işaret
	herkese ulaştığı için bütün oyuncuların tırpanı herkesin ekranında döner.
]]
local TweenService = game:GetService("TweenService")
-- Şimdilik 0 (kapalı): animasyonsuz denemede 180° dönüş bıçağı öne değil yukarı
-- çeviriyor. Dönüş yeni animasyonun içine konacak; gerekirse burası açılır.
local DONUS_ACI = 0        -- derece; tırpan sapı etrafında ne kadar dönsün
local DONUS_SURE = 0.12    -- saniye; dönüş hızı (küçük = daha hızlı)
local GERI_SURE = 0.3      -- saniye; vuruştan sonra geri dönüş (kolla birlikte yumuşak)

local donusBilgi = TweenInfo.new(DONUS_SURE, Enum.EasingStyle.Quad, Enum.EasingDirection.Out)
local geriBilgi = TweenInfo.new(GERI_SURE, Enum.EasingStyle.Quad, Enum.EasingDirection.InOut)

local function tutusKaynagi(alet)
	local karakter = alet.Parent
	local kol = karakter and karakter:FindFirstChild("Right Arm")
	local kaynak = kol and kol:FindFirstChild("RightGrip")
	if kaynak and kaynak:IsA("JointInstance") and kaynak.Part1 == alet:FindFirstChild("Handle") then
		return kaynak
	end
	return nil
end

-- Açıyı bir sayı olarak tween'liyoruz; 180° gibi büyük dönüşlerde CFrame tween'i
-- kısa yolu seçip garip eksende dönebilir, böylece hep sap etrafında döner.
local acilar = {} -- [alet] = NumberValue
local function dondur(alet, ac)
	local kaynak = tutusKaynagi(alet)
	if not kaynak then return end
	local aci = acilar[alet]
	if not aci then
		aci = Instance.new("NumberValue")
		acilar[alet] = aci
		aci.Changed:Connect(function(v)
			local k = tutusKaynagi(alet)
			-- Sap (dırpan) Handle'ın Y ekseni boyunca; Handle'ı kendi Y ekseni etrafında çevir
			if k then k.C1 = CFrame.Angles(0, -math.rad(v), 0) * alet.Grip end
		end)
		alet.Destroying:Connect(function() acilar[alet] = nil; aci:Destroy() end)
	end
	TweenService:Create(aci, ac and donusBilgi or geriBilgi, { Value = ac and DONUS_ACI or 0 }):Play()
end

local function donusBagla(alet)
	if not tirpanMi(alet) or alet:GetAttribute("DonusBagli") then return end
	alet:SetAttribute("DonusBagli", true)
	alet:GetAttributeChangedSignal("swinging"):Connect(function()
		dondur(alet, alet:GetAttribute("swinging") == true)
	end)
end

local function herkesiBagla(baskaOyuncu)
	local function kb(karakter)
		for _, c in ipairs(karakter:GetChildren()) do donusBagla(c) end
		karakter.ChildAdded:Connect(donusBagla)
	end
	if baskaOyuncu.Character then kb(baskaOyuncu.Character) end
	baskaOyuncu.CharacterAdded:Connect(kb)
end

for _, p in ipairs(Players:GetPlayers()) do herkesiBagla(p) end
Players.PlayerAdded:Connect(herkesiBagla)
