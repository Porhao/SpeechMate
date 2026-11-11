"""Narration for the SpeechMate demo video (clear version, 2026-11-10).

One entry per scene: (scene_id, paragraphs, min_seconds). A paragraph is a list of caption chunks:
(english, malay) or (english, malay, tts_text) when the voice needs another spelling ("Speech Mate").
Each scene's lines describe what is on screen, in the order it happens. Scenes tie animations to
chunk numbers (s.at(i)), so keep the meaning of each numbered chunk; extra chunks go at the end.
"""

SCENES = [
    ("s01-mirror", [
        [("When I prepared for interviews or presentations, I practised alone, in front of a mirror.",
          "Semasa bersedia untuk temu duga atau pembentangan, saya berlatih seorang diri, di hadapan cermin.")],
        [("But when I finished, nobody could tell me how I did, or what to improve.",
          "Tetapi selepas selesai, tiada siapa boleh memberitahu prestasi saya, atau apa yang perlu diperbaiki.")],
    ], 15),
    ("s02-problem", [
        [("Many Malaysian students and fresh graduates practise the same way, on their own.",
          "Ramai pelajar dan graduan baharu Malaysia berlatih dengan cara yang sama, seorang diri."),
         ("Yet employers say weak English and communication are why many graduates fail interviews.",
          "Namun majikan berkata kelemahan bahasa Inggeris dan komunikasi menyebabkan ramai graduan gagal temu duga.")],
        [("So I built SpeechMate.", "Jadi saya membina SpeechMate.", "So I built Speech Mate.")],
    ], 14),
    ("s03-intro", [
        [("SpeechMate is an AI speaking coach for Malaysian speakers.", "SpeechMate ialah jurulatih pertuturan AI untuk penutur Malaysia.",
          "Speech Mate is an AI speaking coach for Malaysian speakers."),
         ("It understands English, Bahasa Malaysia and Manglish, the way we really talk.",
          "Ia memahami bahasa Inggeris, Bahasa Malaysia dan Manglish, seperti cara kita bercakap.")],
        [("You can practise job interviews, presentations and daily conversation, each with its own AI partner.",
          "Anda boleh berlatih temu duga, pembentangan dan perbualan harian, setiap satu dengan rakan AI tersendiri."),
         ("Let me show you, step by step.", "Mari saya tunjukkan, langkah demi langkah.")],
    ], 15),
    ("s04-login", [
        [("First, I sign in with my account.", "Mula-mula, saya log masuk ke akaun saya."),
         ("Mate, my friendly companion, appears in the corner and stays with me on every page.",
          "Mate, teman saya, muncul di sudut skrin dan menemani saya di setiap halaman.")],
    ], 10),
    ("s05-home", [
        [("The home page shows the three ways to practise.", "Laman utama menunjukkan tiga cara berlatih."),
         ("Before I start, I set up my profile.", "Sebelum bermula, saya lengkapkan profil saya.")],
    ], 7),
    ("s06-profile", [
        [("In my profile, I choose my level of study, my field, and my goal: job interviews.",
          "Dalam profil, saya pilih tahap pengajian, bidang, dan matlamat saya: temu duga kerja."),
         ("Then my speaking level, and how I like my feedback.", "Kemudian tahap pertuturan saya, dan gaya maklum balas yang saya suka."),
         ("Every AI partner uses this to match my level.", "Setiap rakan AI menggunakan ini untuk menyesuaikan tahap saya.")],
    ], 11),
    ("s07-form", [
        [("Now, the mock interview. I type the job title and the company,",
          "Sekarang, simulasi temu duga. Saya taip jawatan dan nama syarikat,"),
         ("paste the job description, add a little about myself, and upload my resume.",
          "tampal huraian kerja, tulis sedikit tentang diri saya, dan muat naik resume saya."),
         ("Then I click Preview questions.", "Kemudian saya klik Preview questions.")],
    ], 14),
    ("s08-plan", [
        [("The AI writes questions for this exact job: from my resume, the job description, and my own project.",
          "AI menulis soalan untuk jawatan ini: daripada resume saya, huraian kerja, dan projek saya sendiri."),
         ("No generic questions. When I'm ready, I start the interview.",
          "Bukan soalan umum. Apabila sudah bersedia, saya mulakan temu duga.")],
    ], 12),
    ("s09-live", [
        [("Alex, my AI interviewer, asks one question at a time and waits while I answer.",
          "Alex, penemu duga AI saya, bertanya satu soalan pada satu masa dan menunggu saya menjawab.")],
        [("My answer was too short, so Alex asks a follow-up, just like a real interviewer.",
          "Jawapan saya terlalu pendek, jadi Alex bertanya soalan susulan, seperti penemu duga sebenar."),
         ("When I'm done, I click End.", "Apabila selesai, saya klik End.")],
    ], 17),
    ("s09b-analyse", [
        [("Then SpeechMate analyses my session. First, it turns my voice into text.",
          "Kemudian SpeechMate menganalisis sesi saya. Mula-mula, ia menukar suara saya kepada teks.",
          "Then Speech Mate analyses my session. First, it turns my voice into text."),
         ("Next, it checks my pace, filler words and pronunciation, and the camera checks my eye contact and posture.",
          "Seterusnya, ia menyemak rentak, perkataan pengisi dan sebutan, dan kamera menyemak hubungan mata dan postur saya."),
         ("It even notices if I look away when I get stuck, and then it scores my confidence.",
          "Ia juga perasan jika saya mengalihkan pandangan ketika tersekat, kemudian menilai keyakinan saya.")],
    ], 17),
    ("s10-results", [
        [("My results show four simple scores, and for each answer, what went well and a stronger version.",
          "Keputusan saya menunjukkan empat skor mudah, dan bagi setiap jawapan, apa yang baik serta versi yang lebih kukuh."),
         ("It also gives me one main focus, and I can practise it straight away.",
          "Ia juga memberi saya satu fokus utama, dan saya boleh terus berlatih.")],
    ], 14),
    ("s10b-factcheck", [
        [("The stronger answer is checked against what I really said.", "Jawapan yang lebih kukuh disemak dengan apa yang benar-benar saya sebut."),
         ("Here, the AI added a company and a number I never mentioned, so SpeechMate removes them.",
          "Di sini, AI menambah nama syarikat dan nombor yang tidak pernah saya sebut, jadi SpeechMate membuangnya.",
          "Here, the AI added a company and a number I never mentioned, so Speech Mate removes them."),
         ("Only my own facts stay.", "Hanya fakta saya sendiri yang kekal.")],
    ], 12),
    ("s11-deck", [
        [("For presentation practice, I drag in my slides and say who my audience is.",
          "Untuk latihan pembentangan, saya seret slaid saya dan nyatakan siapa penonton saya."),
         ("Before I speak, the AI reads the whole deck and notes the key point of every slide.",
          "Sebelum saya bercakap, AI membaca semua slaid dan mencatat isi utama setiap slaid."),
         ("My talk will be checked against these.", "Pembentangan saya akan disemak berdasarkan isi ini.")],
    ], 17),
    ("s12-talk", [
        [("Then I present at my own pace, while the AI listens quietly.",
          "Kemudian saya membentang mengikut rentak sendiri, sementara AI mendengar dengan senyap."),
         ("On slide two, I skip the main point on purpose, to test it.",
          "Pada slaid dua, saya sengaja tidak menyebut isi utama, untuk mengujinya.")],
    ], 12),
    ("s13-match", [
        [("Afterwards, it compares what I said with each slide, and it caught the missing point on slide two.",
          "Selepas itu, ia membandingkan apa yang saya sebut dengan setiap slaid, dan ia mengesan isi yang tertinggal pada slaid dua."),
         ("So I know exactly what to fix.", "Jadi saya tahu dengan tepat apa yang perlu dibaiki.")],
    ], 11),
    ("s14-qa", [
        [("Next, a Q&A rehearsal, with questions my audience might ask about my own slides.",
          "Seterusnya, latihan soal jawab, dengan soalan yang mungkin ditanya penonton tentang slaid saya sendiri.",
          "Next, a Q and A rehearsal, with questions my audience might ask about my own slides.")],
    ], 10),
    ("s15-convo", [
        [("Daily conversation is for relaxed, everyday practice. I pick a topic and just chat.",
          "Perbualan harian untuk latihan santai setiap hari. Saya pilih topik dan terus berbual."),
         ("I can speak naturally, even in Manglish, and my words are kept exactly as I said them.",
          "Saya boleh bercakap secara biasa, termasuk Manglish, dan perkataan saya dikekalkan seperti yang disebut.")],
    ], 14),
    ("s16-tips", [
        [("Afterwards, it shows what I said next to a more natural way to say it, and explains why.",
          "Selepas itu, ia menunjukkan apa yang saya sebut di sebelah cara yang lebih semula jadi, dan menerangkan sebabnya.")],
    ], 8),
    ("s17-progress", [
        [("The Progress page shows how my scores improve over time, for each type of practice.",
          "Halaman Progress menunjukkan peningkatan skor saya dari semasa ke semasa, bagi setiap jenis latihan.")],
    ], 9),
    ("s17b-mate", [
        [("Not sure what to do next? I just ask Mate.", "Tidak pasti apa seterusnya? Saya cuma tanya Mate."),
         ("Mate knows my profile and past sessions, so it tells me exactly what to practise next.",
          "Mate tahu profil dan sesi lepas saya, jadi ia memberitahu dengan tepat apa yang perlu dilatih seterusnya.")],
    ], 13),
    ("s17c-measured", [
        [("And every score is explained: how it's measured, which model is used, and how to read it.",
          "Dan setiap skor diterangkan: cara ia diukur, model yang digunakan, dan cara membacanya."),
         ("If something can't be measured, it says so instead of guessing.",
          "Jika sesuatu tidak dapat diukur, ia dinyatakan, bukan diteka.")],
    ], 10),
    ("s18-agents", [
        [("Behind SpeechMate is a team of AI agents, each with one job.", "Di sebalik SpeechMate ialah satu pasukan ejen AI, setiap satu dengan satu tugas.",
          "Behind Speech Mate is a team of AI agents, each with one job."),
         ("One plans the questions, one runs the interview, and one reads the slides to check my talk.",
          "Satu merancang soalan, satu menjalankan temu duga, dan satu membaca slaid untuk menyemak pembentangan saya."),
         ("A coach picks drills only from what was measured, so it can't make up problems.",
          "Jurulatih memilih latihan hanya daripada apa yang diukur, jadi ia tidak boleh mereka-reka masalah.")],
        [("And Mate keeps the loop going: practise, get feedback, and practise again.",
          "Dan Mate meneruskan kitaran: berlatih, terima maklum balas, dan berlatih semula.")],
    ], 20),
    ("s19-close", [
        [("Built for Malaysian speakers, private by design, and every score explained.",
          "Dibina untuk penutur Malaysia, privasi terjamin, dan setiap skor diterangkan.")],
        [("No more practising alone in front of the mirror.", "Tiada lagi berlatih seorang diri di hadapan cermin.")],
        [("SpeechMate.", "SpeechMate.", "Speech Mate.")],
    ], 15),
]
