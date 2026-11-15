--[[
	SAMAN BİÇME (SUNUCU) — tırpan savrulduğunda değdiği samanları yok eder.
	Bu bir Script'tir: ServerScriptService içine koy.

	Hangi parçalar saman sayılır? İkisinden biri yeter:
	  • Workspace içinde "Samanlar" adlı bir klasöre koyduğun her şey, ya da
	  • Studio'da Tag Editor ile "Saman" etiketi verdiğin parça veya modeller.
	Saman birden fazla parçadan oluşan bir Model ise, modelin tamamı silinir.

	TirpanSalla (LocalScript) animasyonun "Kes" anında bu script'e haber verir.
]]

local MENZIL = 7          -- tırpanın ulaştığı mesafe (stud). Daha uzak samanlar kesilmez.
local ONE_KAYMA = 3       -- kesme alanının merkezi karakterin kaç stud önünde
local MIN_ARALIK = 1.0    -- iki kesim arasında en az kaç saniye olmalı (hileye karşı)
local ETIKET = "Saman"
local KLASOR_ADI = "Samanlar"

local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local CollectionService = game:GetService("CollectionService")

local samanKes = ReplicatedStorage:FindFirstChild("SamanKes")
if not samanKes then
	samanKes = Instance.new("RemoteEvent")
	samanKes.Name = "SamanKes"
	samanKes.Parent = ReplicatedStorage
end

-- Bir parçanın ait olduğu samanı bul (yoksa nil)
local function samanBul(parca)
	local klasor = workspace:FindFirstChild(KLASOR_ADI)
	local nesne = parca
	while nesne and nesne ~= workspace do
		if CollectionService:HasTag(nesne, ETIKET) then return nesne end
		if klasor and nesne.Parent == klasor then return nesne end
		nesne = nesne.Parent
	end
	return nil
end

local sonKesim = {}

samanKes.OnServerEvent:Connect(function(oyuncu)
	-- Kontroller
	if oyuncu:GetAttribute("SamanAlaninda") ~= true then return end
	local simdi = os.clock()
	if sonKesim[oyuncu] and simdi - sonKesim[oyuncu] < MIN_ARALIK then return end
	sonKesim[oyuncu] = simdi

	local karakter = oyuncu.Character
	local kok = karakter and karakter:FindFirstChild("HumanoidRootPart")
	local humanoid = karakter and karakter:FindFirstChildOfClass("Humanoid")
	if not kok or not humanoid or humanoid.Health <= 0 then return end

	-- Karakterin önündeki alanı tara
	local ileri = kok.CFrame.LookVector
	local merkez = kok.Position + ileri * ONE_KAYMA
	local ayar = OverlapParams.new()
	ayar.FilterType = Enum.RaycastFilterType.Exclude
	ayar.FilterDescendantsInstances = { karakter }

	local silinecek = {}
	for _, parca in ipairs(workspace:GetPartBoundsInRadius(merkez, MENZIL, ayar)) do
		local yon = parca.Position - kok.Position
		if yon:Dot(ileri) > -1 then -- arkadaki samanlar kesilmez
			local saman = samanBul(parca)
			if saman then silinecek[saman] = true end
		end
	end

	for saman in pairs(silinecek) do
		saman:Destroy()
	end
end)

Players.PlayerRemoving:Connect(function(oyuncu)
	sonKesim[oyuncu] = nil
end)
