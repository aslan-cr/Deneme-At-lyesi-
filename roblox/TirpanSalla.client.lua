--[[
	TIRPAN SALLA — tırpanı eline alıp tıklayınca saman biçme animasyonu oynar.
	Bu bir LocalScript'tir: tırpan Tool'unun İÇİNE koy (StarterPack > Tirpan > bu script).
	Tool'un içinde "Handle" adlı bir parça olmalı (tırpan modeli).
	Animasyonu "Publish to Roblox" ile yükledikten sonra çıkan sayıyı ANIM_ID'ye yaz.
]]

local ANIM_ID = "rbxassetid://0" -- <-- buraya kendi animasyon ID'ni yaz
local BEKLEME = 0.3              -- animasyon bittikten sonra yeniden sallamadan önce beklenecek süre (sn)

local tool = script.Parent
local anim = Instance.new("Animation")
anim.AnimationId = ANIM_ID

local track
local mesgul = false

tool.Equipped:Connect(function()
	local karakter = tool.Parent
	local humanoid = karakter:FindFirstChildOfClass("Humanoid")
	if not humanoid then return end
	local animator = humanoid:FindFirstChildOfClass("Animator") or humanoid:WaitForChild("Animator")
	track = animator:LoadAnimation(anim)
	track.Priority = Enum.AnimationPriority.Action
end)

tool.Unequipped:Connect(function()
	if track then track:Stop(0.1) end
	mesgul = false
end)

tool.Activated:Connect(function()
	if mesgul or not track then return end
	mesgul = true
	track:Play(0.1)
	track.Stopped:Wait()
	task.wait(BEKLEME)
	mesgul = false
end)
