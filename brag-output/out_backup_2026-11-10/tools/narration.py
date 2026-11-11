"""Narration for the SpeechMate demo video (concise version, 2026-11-10).

One entry per scene: (scene_id, paragraphs, min_seconds). A paragraph is a list of caption chunks:
(english, malay) or (english, malay, tts_text) when the voice needs another spelling ("Speech Mate").
min_seconds lets the demo keep playing after the voice has finished.
"""

SCENES = [
    ("s01-mirror", [
        [("I used to practise interviews and presentations alone, in front of a mirror.",
          "Dulu saya berlatih temu duga dan pembentangan seorang diri, di hadapan cermin.")],
        [("But a mirror can't tell you what to improve.", "Tetapi cermin tidak dapat memberitahu apa yang perlu diperbaiki.")],
    ], 15),
    ("s02-problem", [
        [("Many Malaysian graduates face the same problem,", "Ramai graduan Malaysia menghadapi masalah yang sama,"),
         ("and employers say communication is where graduates fall short.", "dan majikan berkata komunikasi ialah kelemahan utama graduan.")],
        [("So I built SpeechMate.", "Jadi saya membina SpeechMate.", "So I built Speech Mate.")],
    ], 14),
    ("s03-intro", [
        [("An AI speaking coach for Malaysian speakers,", "Jurulatih pertuturan AI untuk penutur Malaysia,"),
         ("fluent in English, Bahasa Malaysia and Manglish.", "yang memahami bahasa Inggeris, Bahasa Malaysia dan Manglish.")],
        [("Three ways to practise, each with its own AI partner.", "Tiga cara berlatih, setiap satu dengan rakan AI tersendiri."),
         ("Let me show you how it works.", "Mari saya tunjukkan cara ia berfungsi.")],
    ], 15),
    ("s04-login", [
        [("I sign in, and Mate, my companion, joins me.", "Saya log masuk, dan Mate, teman saya, menyertai saya.")],
    ], 10),
    ("s05-home", [
        [("Home shows three ways to practise.", "Laman utama menunjukkan tiga cara berlatih.")],
    ], 7),
    ("s06-profile", [
        [("My profile tells every AI partner my level and my goals.", "Profil saya memberitahu setiap rakan AI tahap dan matlamat saya.")],
    ], 11),
    ("s07-form", [
        [("For a mock interview, I enter the job, the company, and my resume.",
          "Untuk simulasi temu duga, saya masukkan jawatan, syarikat, dan resume saya.")],
    ], 14),
    ("s08-plan", [
        [("The AI plans questions for this exact role, not generic ones.", "AI merancang soalan untuk jawatan ini, bukan soalan umum.")],
    ], 12),
    ("s09-live", [
        [("Alex, my AI interviewer, asks them one by one,", "Alex, penemu duga AI saya, bertanya satu demi satu,"),
         ("and follows up when my answer is too short.", "dan bertanya susulan jika jawapan saya terlalu pendek.")],
    ], 17),
    ("s09b-analyse", [
        [("When I finish, SpeechMate gets to work.", "Selepas saya selesai, SpeechMate mula bekerja.", "When I finish, Speech Mate gets to work."),
         ("Whisper turns my voice into words, MediaPipe reads my eye contact and posture,",
          "Whisper menukar suara saya kepada perkataan, MediaPipe membaca hubungan mata dan postur saya,",
          "Whisper turns my voice into words, Media Pipe reads my eye contact and posture,"),
         ("and Gaze Tunneling checks if I look away right when I stumble.",
          "dan Gaze Tunneling menyemak sama ada saya mengalihkan pandangan tepat ketika tersekat-sekat.")],
    ], 17),
    ("s10-results", [
        [("Afterwards: four clear scores, feedback on every answer,", "Selepas itu: empat skor yang jelas, maklum balas bagi setiap jawapan,"),
         ("and drills for next time.", "dan latihan untuk kali seterusnya.")],
    ], 14),
    ("s10b-factcheck", [
        [("Every stronger answer is fact-checked.", "Setiap jawapan yang lebih kukuh disemak faktanya."),
         ("If the AI adds a name or a number I never said, it's caught and removed.",
          "Jika AI menambah nama atau nombor yang tidak pernah saya sebut, ia dikesan dan dibuang.")],
    ], 12),
    ("s11-deck", [
        [("For presentations, I upload my slides.", "Untuk pembentangan, saya muat naik slaid saya."),
         ("The AI reads the deck first, and notes each slide's key point.", "AI membaca slaid dahulu, dan mencatat isi utama setiap slaid.")],
    ], 17),
    ("s12-talk", [
        [("Then I present at my own pace, while my audience listens.", "Kemudian saya membentang mengikut rentak sendiri, sementara penonton mendengar.")],
    ], 12),
    ("s13-match", [
        [("It checks whether what I said matches each slide, and what I left out.",
          "Ia menyemak sama ada apa yang saya sebut sepadan dengan setiap slaid, dan apa yang tertinggal.")],
    ], 11),
    ("s14-qa", [
        [("Then a Q&A, with questions from my own slides.", "Kemudian sesi soal jawab, dengan soalan daripada slaid saya sendiri.",
          "Then a Q and A, with questions from my own slides.")],
    ], 10),
    ("s15-convo", [
        [("Daily conversation is for everyday practice, Manglish included.", "Perbualan harian untuk latihan setiap hari, termasuk Manglish.")],
    ], 14),
    ("s16-tips", [
        [("Afterwards, it suggests more natural ways to say things.", "Selepas itu, ia mencadangkan cara yang lebih semula jadi untuk menyebutnya.")],
    ], 8),
    ("s17-progress", [
        [("And Progress tracks how I improve over time.", "Dan halaman Progress menjejaki perkembangan saya.")],
    ], 9),
    ("s17b-mate", [
        [("Stuck? I just ask Mate.", "Buntu? Saya cuma tanya Mate."),
         ("It knows my profile and my sessions, and tells me what to practise next.",
          "Ia tahu profil dan sesi saya, dan memberitahu apa yang perlu dilatih seterusnya.")],
    ], 13),
    ("s17c-measured", [
        [("And every number is explained: the method, the model, and how to read it.",
          "Dan setiap nombor diterangkan: kaedahnya, modelnya, dan cara membacanya.")],
    ], 10),
    ("s18-agents", [
        [("Behind it is a team of AI agents.", "Di sebaliknya ialah satu pasukan ejen AI."),
         ("One plans, one interviews, one reads the deck,", "Satu merancang, satu menemu duga, satu membaca slaid,"),
         ("and a coach picks drills only from what was measured.", "dan jurulatih memilih latihan hanya daripada apa yang diukur.")],
        [("Mate keeps the loop going: practise, get feedback, practise again.", "Mate meneruskan kitaran: berlatih, terima maklum balas, berlatih semula.")],
    ], 20),
    ("s19-close", [
        [("Built for Malaysian speakers. Private by design. Every score explained.",
          "Dibina untuk penutur Malaysia. Privasi terjamin. Setiap skor diterangkan.")],
        [("No more practising to the mirror.", "Tiada lagi berlatih di hadapan cermin.")],
        [("SpeechMate.", "SpeechMate.", "Speech Mate.")],
    ], 15),
]
