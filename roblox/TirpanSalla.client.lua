--[[
	TIRPAN SALLA — samanların olduğu yerde ekrana dokununca / sol tıklayınca
	saman biçme animasyonunu oynatır.
	  • Telefon / tablet: ekrana dokun (kaydırma ve joystick sayılmaz)
	  • Bilgisayar: sol tık

	Bu bir LocalScript'tir: StarterPlayer > StarterPlayerScripts içine koy.
	Animasyonu "Publish to Roblox" ile yükledikten sonra çıkan sayıyı ANIM_ID'ye yaz.

	SENİN BAĞLAYACAĞIN YER:
	  Oyuncu samanların olduğu yere girince:   oyuncu:SetAttribute("SamanAlaninda", true)
	  Oradan çıkınca:                          oyuncu:SetAttribute("SamanAlaninda", false)
	  (Bu satırlar sunucu script'inde de, LocalScript'te de çalışır.)

	Tırpan samana değdiği an (animasyondaki "Kes" anı) sunucuya haber verilir,
	ServerScriptService içindeki SamanBicme script'i değdiği samanları yok eder.
]]

local ANIM_ID = "rbxassetid://0" -- <-- buraya kendi animasyon ID'ni yaz
local BEKLEME = 0.3              -- bir biçme bittikten sonra yenisine kadar beklenecek süre (sn)

local Players = game:GetService("Players")
local UserInputService = game:GetService("UserInputService")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local oyuncu = Players.LocalPlayer
local anim = Instance.new("Animation")
anim.AnimationId = ANIM_ID

local samanKes = ReplicatedStorage:WaitForChild("SamanKes") -- SamanBicme (sunucu) script'i oluşturur

local track
local mesgul = false

local function karakterHazir(karakter)
	local humanoid = karakter:WaitForChild("Humanoid")
	local animator = humanoid:WaitForChild("Animator")
	track = animator:LoadAnimation(anim)
	track.Priority = Enum.AnimationPriority.Action
	track.KeyframeReached:Connect(function(ad)
		if ad == "Kes" then samanKes:FireServer() end
	end)
	mesgul = false
end

if oyuncu.Character then task.spawn(karakterHazir, oyuncu.Character) end
oyuncu.CharacterAdded:Connect(karakterHazir)

local function bic()
	if mesgul or not track then return end
	if oyuncu:GetAttribute("SamanAlaninda") ~= true then return end
	mesgul = true
	track:Play(0.1)
	track.Stopped:Wait()
	task.wait(BEKLEME)
	mesgul = false
end

-- Bilgisayar: sol tık
UserInputService.InputBegan:Connect(function(girdi, oyunIsledi)
	if oyunIsledi then return end -- butonlara / menülere tıklama sayılmaz
	if girdi.UserInputType == Enum.UserInputType.MouseButton1 then
		bic()
	end
end)

-- Telefon / tablet: ekrana dokunma (kaydırma değil, kısa dokunuş)
UserInputService.TouchTap:Connect(function(_, oyunIsledi)
	if oyunIsledi then return end -- joystick, zıplama tuşu, menüler sayılmaz
	bic()
end)
