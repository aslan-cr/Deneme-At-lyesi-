"""ElevenLabs seslerini hazır videoya yerleştirir; konuşurken müzik/efektler kısılır (ducking).
Kullanım: python3 mix_voices.py <video.mp4> <ses_klasörü> <1|2> <çıktı.mp4>
Ses dosyası adları: v1_01_disses.mp3 ... (TIMELINE'daki adlar). Eksik dosya atlanır."""
import subprocess, sys, os
TIMELINE = {
  '1': [('v1_01_disses', .3), ('v1_02_disses', 2.9), ('v1_03_mert', 6.6), ('v1_04_disses', 9.3), ('v1_05_sen', 10.4), ('v1_06_disses', 12.4),
        ('v1_07_disses', 16.6), ('v1_08_disses', 21.0), ('v1_09_mert', 23.2), ('v1_10_disses', 27.2), ('v1_11_disses', 31.0)],
  '2': [('v2_01_disses', .3), ('v2_02_sen', 2.7), ('v2_03_anne', 6.2), ('v2_04_sen', 8.7), ('v2_05_disses', 10.2), ('v2_06_sen', 13.6), ('v2_07_anne', 15.3),
        ('v2_08_disses', 17.2), ('v2_09_disses', 19.4), ('v2_10_mert', 26.2), ('v2_11_sen', 28.6), ('v2_12_anne', 32.0), ('v2_13_disses', 35.6)],
}
video, folder, vid, out = sys.argv[1:5]
clips = []
for name, t in TIMELINE[vid]:
    for ext in ('.mp3', '.wav', '.m4a'):
        p = os.path.join(folder, name + ext)
        if os.path.exists(p): clips.append((p, t)); break
    else: print('EKSİK:', name)
if not clips: sys.exit('Hiç ses dosyası bulunamadı.')
args = ['ffmpeg', '-y', '-v', 'error', '-i', video]
for p, _ in clips: args += ['-i', p]
fc = ''.join(f'[{i + 1}:a]aresample=48000,aformat=channel_layouts=stereo,adelay={int(t * 1000)}|{int(t * 1000)},volume=1.6[v{i}];' for i, (_, t) in enumerate(clips))
fc += ''.join(f'[v{i}]' for i in range(len(clips))) + f'amix=inputs={len(clips)}:normalize=0:duration=longest,asplit=2[vo][vk];'
fc += '[0:a]aresample=48000[bg];[bg][vk]sidechaincompress=threshold=0.03:ratio=8:attack=15:release=350[duck];'
fc += '[duck][vo]amix=inputs=2:normalize=0:duration=first,loudnorm=I=-14:TP=-1.5:LRA=11[a]'
args += ['-filter_complex', fc, '-map', '0:v', '-map', '[a]', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-ar', '48000', '-movflags', '+faststart', out]
subprocess.run(args, check=True)
print('Hazır:', out, f'({len(clips)} ses yerleştirildi)')
