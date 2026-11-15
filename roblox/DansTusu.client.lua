--[[
	DANS TUŞU — G tuşuna basınca karakter "Diz Çökme Dansı"nı yapar.
	Bu bir LocalScript'tir: StarterPlayer > StarterPlayerScripts içine koy.
	Animasyonu "Publish to Roblox" ile yükledikten sonra çıkan sayıyı ANIM_ID'ye yaz.
]]

local ANIM_ID = "rbxassetid://0" -- <-- buraya kendi animasyon ID'ni yaz
local TUS = Enum.KeyCode.G

local Players = game:GetService("Players")
local UserInputService = game:GetService("UserInputService")

local oyuncu = Players.LocalPlayer
local anim = Instance.new("Animation")
anim.AnimationId = ANIM_ID

local track

local function karakterHazir(karakter)
	local humanoid = karakter:WaitForChild("Humanoid")
	local animator = humanoid:WaitForChild("Animator")
	track = animator:LoadAnimation(anim)
	track.Priority = Enum.AnimationPriority.Action
	-- Yürümeye başlarsa dansı durdur
	humanoid.Running:Connect(function(hiz)
		if hiz > 1 and track.IsPlaying then track:Stop(0.2) end
	end)
end

if oyuncu.Character then karakterHazir(oyuncu.Character) end
oyuncu.CharacterAdded:Connect(karakterHazir)

UserInputService.InputBegan:Connect(function(girdi, oyunIsledi)
	if oyunIsledi or girdi.KeyCode ~= TUS then return end
	if track and not track.IsPlaying then track:Play(0.1) end
end)
