"""JZL MiniMax Music3 — 多风格 caption 前置节点（V1 经典 API）

输出官方三段式英文 caption（Global Metadata / Vocal Details / Arrangement），
STRING 可直接接到官方「MiniMax Music3 Text Encode」的 caption 输入。

官方参考: comfy_extras/nodes_minimax_music.py — MiniMaxMusic3TextEncode
caption 规范: comfy/ldm/minimax_music/prompt.py — clean_caption / build_prompt
"""


class JZL_MiniMaxMusicCaption:
    """MiniMax Music3 提示词预设 — 多维度标签 → 三段式 caption"""

    # ═══════════════════════════════════════════════════════════
    #  音乐风格库（每个风格三段：global / vocal / arrangement）
    #  写法密度对齐官方 Lo-fi 参考范例
    # ═══════════════════════════════════════════════════════════

    _STYLES = {
        "Lo-fi 嘻哈 / Lo-fi Hip-Hop": {
            "global": "Lo-fi hip-hop, chillhop. Laid-back and dreamy throughout, a gentle warm drift with a subtle late-night glow that deepens in the middle and dissolves softly at the end. Studying, raining-outside, headphones-on late-night listening. Bedroom production: muddy warm texture, heavy vinyl crackle, tape hiss and wow-flutter pitch wobble, low-passed dusty mix, soft-clipped drums, everything slightly detuned and cozy.",
            "vocal": "Soft androgynous vocal, hushed half-sung half-spoken delivery, sitting low in the mix like another instrument, lazy behind-the-beat phrasing, gentle breathy timbre. Sparse murmured double-tracked harmonies, occasional wordless \"mmm\" and \"ooh\" hums drenched in tape delay and warm spring reverb. Long stretches with no vocals at all.",
            "arrangement": "Dusty boom-bap drums with a soft thumping kick, cracked snare with lazy swing, brushed hi-hats, low round sub bass. Warm Rhodes piano chords with slow chorus wobble as the harmonic bed, mellow jazzy guitar licks answering the vocal lines, constant vinyl crackle as texture. Intro: rain and vinyl noise, solo Rhodes chords fading in, drums slipping in halfway. Verses: minimal — drums, bass, Rhodes, soft guitar fills between lines. Instrumental sections: guitar and Rhodes trade relaxed jazzy phrases over the beat, occasional muted trumpet ghost notes far in the background. Bridge: drums drop away to rain, crackle, and floating detuned Rhodes, then the beat eases back in. Outro: elements fade one by one until only vinyl crackle and a last unresolved Rhodes chord remain.",
        },
        "Chillhop / Chillhop": {
            "global": "Chillhop, laid-back instrumental hip-hop. Smooth and unhurried throughout, a mellow late-afternoon glow that stays even and warm from start to finish. Coffee-shop study sessions, rainy-window ambience. Polished lo-fi production: warm rounded bass, soft vinyl crackle, gently low-passed mix, cozy and intimate.",
            "vocal": "Mostly instrumental. If vocals appear, they are rare chopped vocal samples or distant humming phrases, treated like another texture rather than a lead, drifting in and out of the mix.",
            "arrangement": "Relaxed boom-bap drums with a soft kick and snappy rimshot snare, smooth upright bass line, warm electric piano chords, airy Rhodes and gentle flute accents. Intro: filtered vinyl crackle and a slow piano riff fading in, drums joining after a few bars. Verses: minimal groove with bass, keys, and soft drum swing. Chorus: fuller keys and a subtle string pad swell. Bridge: drums strip away to keys and crackle. Outro: a final unresolved piano chord over fading vinyl.",
        },
        "爵士 / Jazz": {
            "global": "Acoustic jazz trio. Warm and sophisticated throughout, smoky and intimate, evoking a dimly lit late-night club. Sipping whisky, low chatter, velvet curtains. Warm analog production: natural room reverb, gentle tape warmth, softly rounded transients.",
            "vocal": "No vocals — a pure instrumental jazz performance led by a breathy saxophone melody that sings like a voice.",
            "arrangement": "Walking double bass, brushed drums with feather-light ride cymbal, comping piano with sparse voicings. Intro: piano and bass set the changes, brushes enter softly. Head: saxophone states the melody over gentle swing. Solos: piano, then sax, trade relaxed phrases while bass walks and brushes keep time. Head reprise: melody returns, slightly ornamented. Outro: a single sustained sax note fading over a final piano chord.",
        },
        "波萨诺瓦 / Bossa Nova": {
            "global": "Bossa nova. Light, breezy, and effortlessly elegant throughout, a gentle seaside afternoon sway. Ocean breeze, sun-dappled terrace, soft clinking glasses. Warm analog production: close-miked nylon guitar, natural room ambience, softly compressed and smooth.",
            "vocal": "Soft, breathy vocal delivered in a gentle half-whisper, relaxed phrasing laid just behind the guitar rhythm, with warm Portuguese-influenced vowel colors.",
            "arrangement": "Nylon-string guitar playing syncopated bossa comping, sparse upright bass on the one and three, whisper-quiet shaker, soft brushed drums. Intro: solo guitar sets the groove. Verses: voice floats over guitar and bass with light percussion. Instrumental break: guitar and piano exchange gentle phrases. Outro: voice hums the melody once more, ending on a suspended guitar chord.",
        },
        "灵魂乐 / Soul": {
            "global": "Classic soul. Warm, rich, and deeply emotional throughout, a slow-burning late-night heartbreak glow. Dimly lit lounge, velvet seats, quiet intimacy. Warm analog production: tube warmth, gentle tape saturation, soft room reverb.",
            "vocal": "Expressive soul vocal with rich vibrato, gospel-tinged runs, and heartfelt phrasing that swells from a whisper to a full-bodied belt, drenched in warm plate reverb.",
            "arrangement": "Slow deep-pocket drums, round electric bass, Rhodes and Hammond organ chords, subtle string section swells. Intro: organ and bass establish a slow groove. Verses: voice carries the melody over minimal backing. Chorus: drums and strings swell behind a soaring vocal. Bridge: everything drops to organ and voice. Outro: ad-libbed vocal runs fading over a final chord.",
        },
        "R&B / R&B": {
            "global": "Contemporary R&B. Smooth, seductive, and polished throughout, a late-night neon glow with a slow pulse. City lights, silk sheets, intimate and hazy. Clean modern production: deep sub bass, tight drums, glassy keys, shimmering reverb tails.",
            "vocal": "Silky lead vocal with modern runs and airy falsetto, intimate and close-miked, layered with soft doubled harmonies and occasional breathy ad-libs.",
            "arrangement": "Trap-influenced slow beat with rolling hi-hats, deep 808 sub bass, glossy electric piano and pads. Intro: filtered chords and a vocal ad-lib. Verses: sparse beat with keys and vocal. Chorus: fuller pads and stacked harmonies. Bridge: beat thins to pads and vocals. Outro: vocal runs dissolve into reverb.",
        },
        "放克 / Funk": {
            "global": "Funk. Groovy, syncopated, and full of swagger throughout, a hot Saturday-night dance floor. Sweaty clubs, mirrored balls, infectious energy. Punchy analog production: tight snappy drums, clean guitar stabs, fat analog synths.",
            "vocal": "Charismatic call-and-response vocal with short rhythmic phrases, shouts, and playful ad-libs, sitting right on top of the groove.",
            "arrangement": "Tight four-on-the-floor drums with a cracking snare, slapping electric bass locked to the kick, rhythmic wah-wah guitar stabs, bright horn section hits. Intro: drums and bass build the groove. Verses: sparse groove with vocal. Chorus: full band with horn punches. Breakdown: rhythm section only, call-and-response. Outro: a final horn hit and stop.",
        },
        "嘻哈 / Hip-Hop": {
            "global": "Hard-hitting hip-hop. Confident, gritty, and rhythmic throughout, a late-night block-party energy. Street corners, car bass, raw momentum. Punchy production: heavy 808 bass, crisp trap snares, dark minor-key loops.",
            "vocal": "Confident rap vocal with sharp rhythmic flow, tight double-time passages, and hard-hitting punchlines, delivered with swagger and occasional ad-libs.",
            "arrangement": "Heavy 808-driven beat with rolling hi-hats, snapping snares, dark piano or synth loop. Intro: filtered loop and a vocal tag. Verses: full rap delivery over the beat. Chorus: anthemic hook with layered vocals. Bridge: beat drops to bass and hi-hats. Outro: the loop fades with a final ad-lib.",
        },
        "电子 / Electronic": {
            "global": "Electronic. Pulsing, hypnotic, and atmospheric throughout, a neon-lit night drive. Synth textures, glowing pads, rhythmic momentum. Clean digital production: wide stereo field, precise transients, deep sub bass.",
            "vocal": "Processed, reverb-soaked vocal fragments floating through the mix, treated as texture with heavy delay and subtle pitch modulation, never leading the track.",
            "arrangement": "Four-on-the-floor kick, layered synth arpeggios, pulsing bassline, airy pads and arpeggiated plucks. Intro: filtered pads build. Build-up: risers and snare rolls raise tension. Drop: full groove with driving bass. Breakdown: pads and vocal fragments. Outro: elements filter away one by one.",
        },
        "氛围 / Ambient": {
            "global": "Ambient. Spacious, weightless, and slowly evolving throughout, a vast drift through soft clouds. Floating in stillness, deep breathing, quiet introspection. Clean production: long reverb tails, no percussion, soft dynamic swells.",
            "vocal": "No vocals — only airy, wordless hums and distant choir-like pads that bloom and fade like light.",
            "arrangement": "Slow-moving pad swells, gentle piano notes with long decay, soft field recordings of wind and distant water. Opening: a single drone rises. Middle: layers of pads breathe in and out. Closing: everything dissolves into a single lingering harmonic.",
        },
        "合成器浪潮 / Synthwave": {
            "global": "Synthwave. Retro-futuristic, neon-drenched, and cinematic throughout, a night drive through a glowing 1980s city. Chrome, neon signs, rain-slicked streets. Vintage synth production: analog warmth, gated reverb, tape saturation.",
            "vocal": "Sparse, filtered female vocal with heavy chorus and delay, delivered in detached melodic phrases like a distant radio transmission.",
            "arrangement": "Driving drum machine beat, pulsing analog bassline, shimmering arpeggios, wide pads. Intro: pads and a rising arp. Verses: bass and drums lock in with vocal. Chorus: anthemic synth lead over the full groove. Bridge: everything thins to a pad. Outro: arps fade into neon haze.",
        },
        "芯片音乐 / Chiptune": {
            "global": "Chiptune. Bright, bouncy, and nostalgic throughout, an 8-bit arcade adventure. Retro game-console energy, pixel skies, heroic optimism. Authentic chip production: square-wave leads, triangle bass, noise-channel drums.",
            "vocal": "No vocals — melodies are carried by bright square-wave leads that sing like game themes.",
            "arrangement": "Square-wave lead melody, triangle-wave bassline, pulse-width modulation chords, noise-channel hi-hats and snare. Intro: title-screen fanfare. Main theme: bouncy melody over bass. Breakdown: melody thins to bass and noise. Outro: the final note holds and fades.",
        },
        "浩室 / House": {
            "global": "House. Deep, groovy, and uplifting throughout, a late-night warehouse pulse. Four-on-the-floor heartbeat, sweaty dance floor, hands in the air. Punchy production: deep kick, swinging percussion, warm chords.",
            "vocal": "Soulful vocal hooks sampled and chopped, repeated hypnotically with delay, short gospel-tinged phrases that lift the groove.",
            "arrangement": "Driving four-on-the-floor kick, swinging hi-hats and claps, warm chord stabs, rolling bassline. Intro: filtered chords and percussion build. Drop: full groove with vocal hook. Breakdown: chords and vocal alone. Build-up: risers and snare rolls. Final drop: everything returns fuller. Outro: groove strips to a kick.",
        },
        "科技舞曲 / Techno": {
            "global": "Techno. Dark, hypnotic, and relentless throughout, a cavernous warehouse at 4 a.m. Industrial textures, strobe light, driving momentum. Raw production: pounding kick, metallic percussion, reverb-drenched atmosphere.",
            "vocal": "Minimal vocals — only sparse, heavily processed spoken fragments and distant industrial whispers used as rhythmic texture.",
            "arrangement": "Pounding kick drum, rolling bassline, metallic hats, clattering percussion, eerie stabs. Intro: percussion layers build. Core: relentless groove with evolving textures. Breakdown: kick drops to a drone. Build-up: tension rises with hats. Final: groove returns harder. Outro: elements strip away to the kick.",
        },
        "鼓打贝斯 / Drum & Bass": {
            "global": "Drum & bass. Fast, high-energy, and intricate throughout, a midnight rave at full speed. Breakneck rhythms, rolling bass, adrenaline rush. Precise production: tight breaks, deep sub bass, crisp transients.",
            "vocal": "Soulful female vocal phrases floating above the chaos, pitched and chopped, offering brief melodic respites between drops.",
            "arrangement": "Amen-style breakbeats at 170+ BPM, deep wobbling sub bass, atmospheric pads, syncopated stabs. Intro: pads and vocals. Build-up: rising riser and break fills. Drop: full-speed drums and bass. Breakdown: pads and vocal. Second drop: heavier bassline. Outro: drums cut to a final sub hit.",
        },
        "摇滚 / Rock": {
            "global": "Rock. Gritty, driving, and full of attitude throughout, a sweaty club show. Distorted guitars, pounding drums, raw energy. Punchy production: crunchy guitars, tight drums, slightly overdriven mix.",
            "vocal": "Raspy, powerful male vocal delivered with grit and range, rising from a growl in the verses to a soaring belt in the chorus.",
            "arrangement": "Driving drums, distorted power-chord guitars, pulsing bass, anthemic lead riffs. Intro: guitar riff kicks in. Verses: vocal over driving chords. Chorus: full band at maximum, soaring vocal. Guitar solo: melodic and fiery. Bridge: dynamics drop then rebuild. Outro: a final chord rings out.",
        },
        "独立民谣 / Indie Folk": {
            "global": "Indie folk. Tender, organic, and intimate throughout, a cabin in the woods at golden hour. Campfire warmth, falling leaves, quiet storytelling. Warm acoustic production: close-miked instruments, natural room ambience, soft tape warmth.",
            "vocal": "Gentle, confessional vocal with a slight rasp, sung close to the mic with honest, unadorned phrasing and soft harmonies in the chorus.",
            "arrangement": "Fingerpicked acoustic guitar, soft banjo and mandolin accents, upright bass, light brushed percussion. Intro: solo guitar melody. Verses: voice and guitar, sparse. Chorus: harmonies and light percussion swell. Bridge: strings drift in. Outro: a final guitar note rings over silence.",
        },
        "原声吉他 / Acoustic": {
            "global": "Solo acoustic guitar. Warm, intimate, and unhurried throughout, a quiet morning by the window. Coffee steam, soft sunlight, peaceful stillness. Natural production: close-miked with warm room tone, no effects beyond gentle reverb.",
            "vocal": "No vocals — the guitar alone carries every melody and emotion.",
            "arrangement": "Fingerpicked arpeggios and gentle strumming, with a soft melody line woven through the chords. Opening: a slow picking pattern establishes the mood. Middle: the melody rises and falls. Closing: the final chord decays into silence.",
        },
        "钢琴 / Piano": {
            "global": "Solo piano. Delicate, expressive, and introspective throughout, a quiet candlelit room. Rain on glass, slow thoughts, gentle melancholy. Natural production: warm close-miked piano, soft pedal noise, natural decay.",
            "vocal": "No vocals — the piano alone sings every phrase.",
            "arrangement": "Sparse left-hand chords under a singing right-hand melody, with gentle rubato and long pauses. Opening: a simple motif. Middle: the motif develops and swells. Closing: the opening theme returns, softer, ending on an unresolved chord.",
        },
        "管弦乐 / Orchestral": {
            "global": "Full orchestra. Grand, sweeping, and cinematic throughout, a vast score for an epic story. Concert-hall acoustics, soaring strings, majestic brass. Rich production: wide dynamic range, natural hall reverb, detailed sections.",
            "vocal": "No solo vocals — an optional wordless choir rises in the climax like a distant heavenly voice.",
            "arrangement": "Sweeping string melodies, warm French horn chorales, woodwind colors, timpani and cymbal accents. Opening: soft strings establish a theme. Build: brass and percussion swell. Climax: full orchestra at maximum. Denouement: strings alone. Ending: a final quiet chord.",
        },
        "史诗 / Epic": {
            "global": "Epic cinematic score. Powerful, heroic, and larger than life throughout, a battle cry on a grand scale. Thundering drums, soaring choirs, world-shaking intensity. Huge production: massive percussion, wall-of-sound strings, dramatic swells.",
            "vocal": "Powerful wordless choir chanting over the climax, layered male and female voices rising like an army's anthem.",
            "arrangement": "Thundering taiko drums, relentless string ostinatos, blaring brass fanfares, choir swells. Opening: low strings and drums build. Rises: tension climbs step by step. Climax: full choir and orchestra explode. Aftermath: strings fade. Ending: a final drum hit and silence.",
        },
        "浪漫弦乐 / Romantic Strings": {
            "global": "Romantic strings. Lush, tender, and sweeping throughout, a candlelit waltz under starlight. Slow dances, soft embraces, timeless elegance. Rich production: warm vibrato, soaring legato lines, gentle hall reverb.",
            "vocal": "No vocals — the strings themselves sing the melody with aching lyricism.",
            "arrangement": "Lush violin melody over warm cello and viola harmonies, with harp glissandos and delicate pizzicato. Opening: cello introduces a theme. Middle: violins soar in unison. Swell: full section in passionate vibrato. Ending: the melody dissolves into a single held note.",
        },
        "悬疑 / Suspense": {
            "global": "Suspenseful thriller score. Tense, creeping, and unsettling throughout, a shadow moving at the edge of sight. Dark corridors, held breath, quiet dread. Detailed production: close-miked textures, deep drones, sudden silences.",
            "vocal": "No vocals — only eerie, wordless whispers and distant humming used as texture.",
            "arrangement": "Low-frequency drones, sparse piano notes, ticking percussion, dissonant string clusters. Opening: a low drone and a heartbeat pulse. Build: textures layer and tighten. Stabs: sudden dissonant hits. Release: silence, then a whisper. Ending: an unresolved note hangs.",
        },
        "国风民乐 / Chinese Folk": {
            "global": "Traditional Chinese folk music. Graceful, poetic, and evocative throughout, a misty mountain landscape at dawn. Ink-wash scenery, flowing rivers, ancient villages. Natural production: close-miked instruments, gentle room ambience, unhurried phrasing.",
            "vocal": "Ethereal female vocal with soft vibrato, singing a pentatonic melody like a distant mountain song, occasionally humming wordlessly.",
            "arrangement": "Guzheng glissandos, erhu melodic lines, dizi bamboo flute trills, pipa tremolos. Opening: guzheng sets a flowing texture. Theme: erhu and flute trade phrases. Middle: pipa adds rhythmic color. Ending: flute fades over a guzheng echo.",
        },
        "古琴 / Guqin": {
            "global": "Solo guqin. Deep, meditative, and profoundly still throughout, a scholar's study in moonlight. Incense smoke, still water, ancient wisdom. Natural production: intimate close-miking, every string texture and finger slide audible.",
            "vocal": "No vocals — only the guqin's resonant strings and occasional soft harmonic overtones.",
            "arrangement": "Slow, sparse plucked phrases with long silences between notes, subtle slides and harmonics. Opening: a single deep note. Middle: phrases unfold like breath. Closing: harmonics fade into silence.",
        },
        "戏曲 / Chinese Opera": {
            "global": "Stylized Chinese opera. Dramatic, theatrical, and intensely expressive throughout, a stage of painted faces and flowing robes. Gongs and clappers, piercing falsetto, ancient drama. Traditional production: live stage acoustics, bright percussion, unprocessed vocals.",
            "vocal": "Piercing theatrical vocal in traditional opera style, alternating between dramatic declamation and high falsetto, ornamented with vibrato and slides.",
            "arrangement": "Clanging gongs, wooden clappers, piercing erhu, bamboo flute. Opening: gong and clappers announce. Recitation: vocal declaims over sparse percussion. Aria: full band with expressive vocal. Climax: gongs crash. Ending: a final clap and silence.",
        },
        "冥想 / Meditation": {
            "global": "Meditative soundscape. Calm, grounding, and deeply peaceful throughout, a still morning beside a temple. Slow breathing, soft light, inner quiet. Pure production: long tones, no sharp transients, gentle swells.",
            "vocal": "Soft wordless humming and long vowel tones, like a gentle chant, floating above the drones.",
            "arrangement": "Singing bowls, slow drone pads, soft wind chimes, distant flute. Opening: a singing bowl rings. Middle: drones and bowls layer softly. Closing: everything fades to a single pure tone.",
        },
        "自然白噪音 / Nature Ambient": {
            "global": "Nature ambience. Organic, soothing, and immersive throughout, a rainforest at dawn. Rain on leaves, distant birds, flowing streams. Field-recording production: untouched natural textures, gentle spatial depth, no melody.",
            "vocal": "No vocals — only birdsong and wind carry the soundscape.",
            "arrangement": "Layered field recordings of rain, wind through trees, distant thunder, birdsong and crickets. Opening: rain fades in. Middle: birds and wind join. Closing: rain alone, fading softly.",
        },
        # ── 官方 genre-router 家族补充 ──
        "华语流行 / Mandopop": {
            "global": "Mandopop, contemporary Chinese pop. Melodic, heartfelt, and polished throughout, a warm city-pop glow with modern production sheen. Late-night drives, city lights, youthful longing. Clean modern production: bright keys, glossy synths, tight punchy mix with a subtle electronic flavor.",
            "vocal": "Warm, expressive Chinese vocal with clear diction and gentle vibrato, emotional phrasing that rises from intimate verses into an open, soaring chorus, with soft doubled harmonies and airy backing layers.",
            "arrangement": "Mid-tempo pop beat with crisp drums and a round bassline, warm electric piano and glossy synth pads, subtle guitar arpeggios. Intro: filtered keys and a soft vocal breath. Verses: minimal beat with keys and vocal. Pre-chorus: tension builds with rising pads. Chorus: full band, soaring vocal, stacked harmonies. Bridge: everything thins to piano and voice. Outro: the hook fades over a final chord.",
        },
        "国风流行 / Guofeng Pop": {
            "global": "Guofeng pop, a Chinese-style pop ballad blending traditional and modern elements. Poetic, graceful, and deeply evocative throughout, ink-wash imagery and ancient longing. Moonlit pavilions, falling blossoms, flowing robes. Hybrid production: traditional Chinese instruments woven into a modern ballad mix.",
            "vocal": "Ethereal, emotive vocal with soft vibrato and delicate ornamentation, delivered in a flowing legato style with occasional airy falsetto and gentle layered harmonies.",
            "arrangement": "Piano and guzheng share the harmonic bed, with erhu melodic lines, dizi flute accents, and subtle electronic pads over a slow pop beat. Intro: guzheng glissando over piano. Verses: sparse piano and vocal with guzheng echoes. Chorus: drums enter with strings and dizi, vocal soars. Bridge: erhu solo over pads. Outro: a single guzheng note fades.",
        },
        "流行 / Pop": {
            "global": "Contemporary pop. Bright, catchy, and universally appealing throughout, a polished radio-ready sound. Hooks, tight production, wide appeal. Clean modern production: crisp drums, deep bass, glossy synths, shimmering top end.",
            "vocal": "Clear, confident lead vocal with a bright, radio-friendly tone, strong hook delivery, layered harmonies and ad-libs, subtly pitch-polished.",
            "arrangement": "Upbeat pop beat, punchy bass, sparkling synths, rhythmic guitar, anthemic hooks. Intro: hooky instrumental riff. Verses: sparse beat with vocal. Pre-chorus: tension builds. Chorus: massive hook with stacked harmonies. Bridge: stripped-back moment. Final chorus: everything returns bigger. Outro: the hook fades out.",
        },
        "金属 / Metal": {
            "global": "Metal, heavy and aggressive throughout, a wall of distorted guitars and thunderous drums. Raw intensity, chugging riffs, visceral power. Punchy production: heavily distorted guitars, tight double-kick drums, roaring low end.",
            "vocal": "Harsh, powerful vocal alternating between a guttural growl and a soaring melodic clean chorus, delivered with maximum intensity and occasional gang shouts.",
            "arrangement": "Driving double-kick drums, palm-muted chugging riffs, screaming lead guitar, roaring bass. Intro: a fast riff and drum fill kick in. Verses: chugging guitars under growled vocals. Chorus: melodic clean vocal over soaring chords. Breakdown: half-time heaviness. Guitar solo: fast and technical. Outro: a final chug ends abruptly.",
        },
        "布鲁斯 / Blues": {
            "global": "Traditional blues. Gritty, soulful, and deeply felt throughout, a smoky back-room juke joint. Slow-burning twelve-bar changes, call-and-response, raw honesty. Vintage production: warm tube amps, room ambience, unpolished and honest.",
            "vocal": "Weathered, gravelly vocal with bent notes and heartfelt phrasing, alternating between a spoken growl and a full-throated wail, full of call-and-response character.",
            "arrangement": "Twelve-bar blues progression with a walking bass, shuffle drums, rhythmic rhythm guitar, and expressive lead guitar fills. Intro: a slow bluesy guitar riff. Verses: vocal over the shuffle with guitar answers. Solos: smoky, bluesy guitar and harmonica trade phrases. Outro: the band winds down to a final bent note.",
        },
        "乡村 / Country": {
            "global": "Country, warm and down-to-earth throughout, a dusty backroad at sunset. Storytelling, pedal steel, honest roots. Warm production: close-miked acoustic instruments, natural room ambience, gentle twang.",
            "vocal": "Warm, twangy vocal with sincere, storytelling delivery and a slight southern drawl, joined by tight close harmonies on the chorus.",
            "arrangement": "Acoustic and electric guitars, pedal steel swells, fiddle accents, upright bass, brushed snare. Intro: acoustic guitar and pedal steel. Verses: vocal over strumming. Chorus: full band with harmonies and fiddle. Bridge: pedal steel solo. Outro: guitar and steel fade together.",
        },
        "摇摆爵士 / Swing & Big Band": {
            "global": "Big band swing. Bouncy, brassy, and exuberant throughout, a 1940s dance hall in full swing. Tight horn sections, swinging rhythm, vintage glamour. Authentic production: bright brass, natural room reverb, vintage mono warmth.",
            "vocal": "Charismatic crooner vocal with a warm, rounded tone and effortless swing phrasing, occasionally joined by playful scat syllables and call-and-response with the band.",
            "arrangement": "Tight brass section with trumpets, trombones, and saxophones, swinging rhythm guitar, walking bass, and crisp hi-hat drums. Intro: full band hits a swinging riff. Head: vocal over the swing. Solos: trumpet, sax, and trombone trade phrases. Final chorus: shout chorus with the full band. Outro: a final brass stab.",
        },
        "迪斯科 / Disco": {
            "global": "Disco. Glittering, euphoric, and endlessly danceable throughout, a mirrored dance floor under a spinning ball. Four-on-the-floor pulse, lush strings, funky bass. Shimmering production: sparkling strings, punchy drums, wide dance-floor mix.",
            "vocal": "Smooth, soaring vocal with rich harmonies and falsetto lifts, delivered with disco flair and echoed call-and-response phrases.",
            "arrangement": "Four-on-the-floor kick, walking octave bass, wah-wah rhythm guitar, lush string section, bright horns. Intro: strings and bass build. Verses: vocal over the pulse. Chorus: full band with strings and harmonies. Breakdown: percussion and bass. Final chorus: everything returns bigger. Outro: a final string hit.",
        },
        "出神 / Trance": {
            "global": "Trance. Uplifting, euphoric, and hypnotic throughout, a vast festival mainstage at night. Sweeping supersaws, rolling bass, hands-in-the-air breakdowns. Huge production: wide supersaw stacks, driving fast kick, epic reverb-drenched builds.",
            "vocal": "Ethereal female vocal floating above the mix with reverb-drenched phrases and airy harmonies, providing brief melodic hooks between the drops.",
            "arrangement": "Driving four-on-the-floor kick, rolling bassline, shimmering arpeggios, sweeping supersaw pads. Intro: pads and arps build. Breakdown: vocal and pads with a long build. Drop: full supersaw wall of sound. Second breakdown: emotional piano and vocal. Final drop: everything returns euphoric. Outro: pads fade into silence.",
        },
        "雷鬼 / Reggae": {
            "global": "Reggae. Laid-back, rhythmic, and sun-soaked throughout, an island afternoon sway. Offbeat skank guitar, deep bass, irie vibrations. Warm production: analog warmth, deep sub bass, laid-back groove.",
            "vocal": "Relaxed, soulful vocal with a melodic, conversational delivery, singing with warmth and occasional harmony backing, easy and unhurried.",
            "arrangement": "Offbeat skank guitar, deep round bassline, one-drop drums with rimshot accents, bright organ stabs. Intro: bass and skank set the groove. Verses: vocal floats over the one-drop. Chorus: harmonies lift. Instrumental: melodica or guitar solo. Outro: groove fades into dub echo.",
        },
    }

    # 官方 genre-router 18 家族未覆盖、节点额外补充的风格（其余均标 [官方]）
    _SUPPLEMENT_STYLES = {
        "芯片音乐 / Chiptune",
        "冥想 / Meditation",
        "自然白噪音 / Nature Ambient",
    }

    # ═══════════════════════════════════════════════════════════
    #  可选维度 hint（值为英文短句，拼进 Global Metadata / Vocal Details）
    # ═══════════════════════════════════════════════════════════

    _BPM_HINTS = {
        "不指定 / Unspecified": "",
        "慢速 60-75 / Slow 60-75 BPM": "60-75 BPM",
        "中速 80-100 / Mid 80-100 BPM": "80-100 BPM",
        "快速 110-135 / Fast 110-135 BPM": "110-135 BPM",
        "极快 140+ / Very Fast 140+ BPM": "140+ BPM",
    }

    _KEY_HINTS = {
        "不指定 / Unspecified": "",
        # 调式/音阶
        "大调 / Major": "major key",
        "小调 / Minor": "minor key",
        "五声音阶 / Pentatonic": "pentatonic scale",
        "爵士扩展 / Jazzy Extensions": "major scale with jazzy extensions",
        "多利亚 / Dorian": "Dorian mode",
        "混合利底亚 / Mixolydian": "Mixolydian mode",
        # 12 大调
        "C 大调 / C Major": "C major",
        "降D 大调 / D-flat Major": "D-flat major",
        "D 大调 / D Major": "D major",
        "降E 大调 / E-flat Major": "E-flat major",
        "E 大调 / E Major": "E major",
        "F 大调 / F Major": "F major",
        "升F 大调 / F-sharp Major": "F-sharp major",
        "G 大调 / G Major": "G major",
        "降A 大调 / A-flat Major": "A-flat major",
        "A 大调 / A Major": "A major",
        "降B 大调 / B-flat Major": "B-flat major",
        "B 大调 / B Major": "B major",
        # 12 小调
        "C 小调 / C Minor": "C minor",
        "升C 小调 / C-sharp Minor": "C-sharp minor",
        "D 小调 / D Minor": "D minor",
        "降E 小调 / E-flat Minor": "E-flat minor",
        "E 小调 / E Minor": "E minor",
        "F 小调 / F Minor": "F minor",
        "升F 小调 / F-sharp Minor": "F-sharp minor",
        "G 小调 / G Minor": "G minor",
        "升G 小调 / G-sharp Minor": "G-sharp minor",
        "A 小调 / A Minor": "A minor",
        "降B 小调 / B-flat Minor": "B-flat minor",
        "B 小调 / B Minor": "B minor",
    }

    _MOOD_HINTS = {
        "不指定 / Unspecified": "",
        "梦幻 / Dreamy": "Dreamy and ethereal",
        "放松 / Laid-back": "Laid-back and relaxed",
        "温暖 / Warm": "Warm and comforting",
        "忧郁 / Melancholic": "Melancholic and wistful",
        "高能 / Energetic": "Energetic and driving",
        "紧张 / Tense": "Tense and suspenseful",
        "神秘 / Mysterious": "Mysterious and haunting",
        "神圣 / Ethereal": "Ethereal and celestial",
        "浪漫 / Romantic": "Romantic and tender",
        "悲伤 / Sad": "Sad and sorrowful",
        "希望 / Hopeful": "Hopeful and uplifting",
        "迷幻 / Psychedelic": "Psychedelic and trippy",
        "庄严 / Solemn": "Solemn and reverent",
    }

    _SCENE_HINTS = {
        "不指定 / Unspecified": "",
        "学习 / Studying": "Studying",
        "雨夜 / Raining Outside": "Raining outside",
        "深夜耳机 / Late-night Headphones": "Headphones-on late-night listening",
        "驾驶 / Driving": "Night driving",
        "健身 / Workout": "Workout",
        "冥想 / Meditation": "Meditation and deep focus",
        "咖啡店 / Coffee Shop": "Cozy coffee shop",
        "睡前 / Bedtime": "Winding down before bed",
        "派对 / Party": "Party",
        "游戏 / Gaming": "Gaming",
        "通勤 / Commute": "Commuting",
        "温泉 / Spa": "Spa and relaxation",
        "晨间 / Morning": "Morning",
        "黄昏 / Sunset": "Golden-hour sunset",
        "跑步 / Running": "Running",
    }

    # 人声拆为三个轴：配置(性别) / 音色 / 唱法，自由组合；和声单独控制
    _VOCAL_CONFIG_HINTS = {
        "跟随风格 / Follow Style": "",
        "无人声 / Instrumental (No Vocals)": "No vocals at all — a pure instrumental arrangement, every melody carried by instruments.",
        "女声 / Female Vocal": "female vocal",
        "男声 / Male Vocal": "male vocal",
        "童声 / Child Vocal": "child's voice",
        "柔和中性 / Soft Androgynous Vocal": "soft androgynous vocal",
        "合唱 / Choir": "layered choir",
    }

    _REGISTER_HINTS = {
        "跟随风格 / Follow Style": "",
        "女高音 / Soprano": "soprano",
        "女中音 / Mezzo-Soprano": "mezzo-soprano",
        "女低音 / Alto": "alto",
        "男高音 / Tenor": "tenor",
        "男中音 / Baritone": "baritone",
        "男低音 / Bass": "bass",
    }

    _VOCAL_TIMBRE_HINTS = {
        "跟随风格 / Follow Style": "",
        "清亮 / Clear Bright": "clear, bright",
        "温暖 / Warm": "warm",
        "烟嗓 / Smoky Husky": "smoky, husky",
        "沧桑 / Weathered Gravelly": "weathered, gravelly",
        "气声 / Breathy": "breathy",
        "空灵 / Ethereal Airy": "ethereal, airy",
        "浑厚 / Deep Rich": "deep, rich",
        "磁性 / Magnetic": "magnetic, rich",
        "慵懒 / Lazy Laid-Back": "lazy, laid-back",
        "纯净 / Pure Clean": "pure, clean",
    }

    _VOCAL_STYLE_HINTS = {
        "跟随风格 / Follow Style": "",
        "假声 / Falsetto": "falsetto delivery",
        "半说半唱 / Half-Sung Half-Spoken": "half-sung half-spoken delivery",
        "说唱 / Rap Flow": "rap flow",
        "呼麦 / Throat Singing": "throat singing (khoomei)",
        "民谣 / Folk Storytelling": "folk storytelling delivery",
        "美声 / Bel Canto": "operatic bel canto delivery",
        "颤音 / Vibrato": "expressive vibrato",
        "戏腔 / Chinese Opera Style": "Chinese opera-style delivery with ornamented vibrato and slides",
        "吟唱 / Chant": "chant-like, repetitive phrasing",
        "约德尔 / Yodeling": "yodeling with rapid register breaks",
        "嘶吼 / Growl": "guttural growl",
    }

    _HARMONY_HINTS = {
        "跟随风格 / Follow Style": "",
        "无和声 / No Harmony": "no harmony",
        "双声部和声 / Double-Tracked Harmonies": "tight double-tracked harmonies",
        "多人叠唱 / Stacked Harmonies": "stacked multi-voice harmonies",
        "伴唱垫底 / Backing Vocals": "soft backing vocals underneath",
    }

    _VOCAL_FX_HINTS = {
        "跟随风格 / Follow Style": "",
        "磁带延迟 / Tape Delay": "drenched in tape delay and warm spring reverb",
        "暖混响 / Warm Reverb": "drenched in warm plate reverb",
        "自动调音 / Auto-Tune": "subtle Auto-Tune polish with a modern sheen",
        "干声无效果 / Dry (No FX)": "dry, close-miked vocal with no audible effects",
        "回声 / Echo": "spacious echo and gentle slap-back delay",
    }

    _TEXTURE_HINTS = {
        "跟随风格 / Follow Style": "",
        "干净数字 / Clean Digital": "Clean digital production: crisp highs, tight low end, polished mix with no noise or lo-fi artifacts.",
        "温暖模拟 / Warm Analog": "Warm analog production: soft saturation, gentle tube warmth, slightly rounded transients.",
        "磁带 Lo-fi / Tape Lo-fi": "Tape lo-fi production: heavy tape hiss, wow-and-flutter pitch wobble, low-passed dusty mix, everything slightly detuned and cozy.",
        "黑胶噪点 / Vinyl Crackle": "Vinyl production: constant crackle and surface noise, warm low end, vintage EQ curve.",
    }

    _METER_HINTS = {
        "不指定 / Unspecified": "",
        "4/4": "4/4 time",
        "3/4": "3/4 waltz time",
        "6/8": "6/8 time",
        "12/8": "12/8 shuffle",
        "2/4": "2/4 time",
        "5/4": "5/4 time",
        "7/8": "7/8 time",
    }

    _CONTOUR_HINTS = {
        "不指定 / Unspecified": "",
        # 渐变型：能量单调上行/下行
        "由静到扬 / Gradual Rise": "a gradual emotional rise that opens calm and builds steadily into an uplifting peak",
        "由扬到静 / Gradual Fade": "a gradual emotional fade that opens energetic and steadily settles into a calm close",
        # 反转型：有明显的「抑↔扬」转折对比
        "先抑后扬 / Suppressed→Erupt": "a reversal arc that holds the mood low and restrained, then erupts into a climactic release",
        "先扬后抑 / Peak→Dissolve": "a reversal arc that opens at an emotional peak, then falls and dissolves into quiet",
        # 平稳型：情绪恒定
        "持续平静 / Steady Calm": "a steady, even emotional contour that stays calm and unhurried throughout",
        "持续高能 / Steady Energetic": "a steady, high-energy emotional contour that stays intense and driving throughout",
        # 复合型：多次起伏
        "起承转合 / Rise-Fall-Rise": "a classic rise-fall-rise emotional arc with tension building, releasing, and building again",
        "跌宕起伏 / Rollercoaster": "repeated dramatic swings between tension and release, with multiple emotional peaks and valleys",
    }

    _STRUCTURE_HINTS = {
        "跟随风格 / Follow Style": "",
        "标准流行 / Standard Pop": "Song structure: Intro → Verse → Pre-Chorus → Chorus → Verse → Chorus → Bridge → Final Chorus → Outro",
        "简洁 / Compact": "Song structure: Verse → Chorus → Verse → Chorus → Outro",
        "无 Intro / No Intro": "Song structure: Verse → Pre-Chorus → Chorus → Verse → Chorus → Bridge → Outro",
        "含器乐间奏 / With Instrumental Break": "with an instrumental break between the second chorus and the bridge",
        "含 Breakdown / With Breakdown": "with a stripped-down breakdown before the final chorus",
    }

    @classmethod
    def INPUT_TYPES(s):
        # 官方优先，补充靠后；组内保持定义顺序
        _keys = sorted(s._STYLES.keys(), key=lambda k: k in s._SUPPLEMENT_STYLES)
        style_list = [("[官方] " if k not in s._SUPPLEMENT_STYLES else "[补充] ") + k for k in _keys]
        fusion_list = ["不指定 / Unspecified"] + style_list
        return {
            "required": {
                "音乐风格": (style_list, {
                    "default": style_list[0],
                    "tooltip": "官方 Structured Caption 三段式：Global Metadata（genre/BPM/key/拍号/情绪/情绪演变/场景/制作）/ Vocal Details（配置/音区/音色/唱法/和声/效果）/ Arrangement（分段时间线）",
                }),
                "风格融合": (fusion_list, {
                    "default": "不指定 / Unspecified",
                    "tooltip": "官方 genre-router 支持双风格融合，副风格以 influences 形式并入 Global Metadata",
                }),
                "速度": (list(s._BPM_HINTS.keys()), {"default": "不指定 / Unspecified"}),
                "调性": (list(s._KEY_HINTS.keys()), {"default": "不指定 / Unspecified"}),
                "拍号": (list(s._METER_HINTS.keys()), {"default": "不指定 / Unspecified"}),
                "情绪氛围": (list(s._MOOD_HINTS.keys()), {"default": "不指定 / Unspecified"}),
                "情绪演变": (list(s._CONTOUR_HINTS.keys()), {"default": "不指定 / Unspecified"}),
                "使用场景": (list(s._SCENE_HINTS.keys()), {"default": "不指定 / Unspecified"}),
                "段落结构": (list(s._STRUCTURE_HINTS.keys()), {"default": "跟随风格 / Follow Style"}),
                "人声配置": (list(s._VOCAL_CONFIG_HINTS.keys()), {"default": "跟随风格 / Follow Style"}),
                "声部音区": (list(s._REGISTER_HINTS.keys()), {"default": "跟随风格 / Follow Style"}),
                "人声音色": (list(s._VOCAL_TIMBRE_HINTS.keys()), {"default": "跟随风格 / Follow Style"}),
                "人声唱法": (list(s._VOCAL_STYLE_HINTS.keys()), {"default": "跟随风格 / Follow Style"}),
                "和声伴唱": (list(s._HARMONY_HINTS.keys()), {"default": "跟随风格 / Follow Style"}),
                "人声效果": (list(s._VOCAL_FX_HINTS.keys()), {"default": "跟随风格 / Follow Style"}),
                "制作质感": (list(s._TEXTURE_HINTS.keys()), {
                    "default": "跟随风格 / Follow Style",
                    "tooltip": "覆盖 caption 的制作质感描述。官方节点 cfg_scale（默认 1.5，CFG 引导强度）与 top_k（默认 50，采样候选截断）请在其高级参数中设置，本节点不改动",
                }),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("caption",)
    FUNCTION = "build"
    CATEGORY = "JZL/MiniMax"

    @staticmethod
    def _en(label: str) -> str:
        return label.split(" / ")[-1]

    def _compose_vocal(self, style: dict, config_key: str, register_key: str,
                       timbre_key: str, style_key: str, harmony_key: str) -> str:
        if config_key == "无人声 / Instrumental (No Vocals)":
            return self._VOCAL_CONFIG_HINTS[config_key]
        config = self._VOCAL_CONFIG_HINTS.get(config_key, "")
        register = self._REGISTER_HINTS.get(register_key, "")
        timbre = self._VOCAL_TIMBRE_HINTS.get(timbre_key, "")
        delivery = self._VOCAL_STYLE_HINTS.get(style_key, "")
        harmony = self._HARMONY_HINTS.get(harmony_key, "")
        if not (config or register or timbre or delivery or harmony):
            return style["vocal"]
        parts = [p for p in (timbre, register, config) if p]
        subject = " ".join(parts).strip() if parts else "lead vocal"
        clauses = [c for c in (delivery, harmony) if c]
        if clauses:
            return subject + " with " + " and ".join(clauses)
        return subject

    def build(self, 音乐风格: str, 风格融合: str, 速度: str, 调性: str, 拍号: str, 情绪氛围: str,
              情绪演变: str, 使用场景: str, 段落结构: str, 人声配置: str, 声部音区: str, 人声音色: str,
              人声唱法: str, 和声伴唱: str, 人声效果: str, 制作质感: str) -> tuple[str]:
        style_key = 音乐风格
        for prefix in ("[官方] ", "[补充] "):
            if style_key.startswith(prefix):
                style_key = style_key[len(prefix):]
                break
        style = self._STYLES.get(style_key)
        if style is None:
            raise ValueError(f'未知音乐风格: "{音乐风格}"')

        # Global Metadata：风格本体 + 可选维度追加（BPM/key/拍号/情绪/情绪演变/场景/融合/质感）
        extras = [h for h in (
            self._BPM_HINTS.get(速度, ""),
            self._KEY_HINTS.get(调性, ""),
            self._METER_HINTS.get(拍号, ""),
            self._MOOD_HINTS.get(情绪氛围, ""),
            self._CONTOUR_HINTS.get(情绪演变, ""),
            self._SCENE_HINTS.get(使用场景, ""),
        ) if h]
        if "不指定" not in 风格融合:
            extras.append(f"fused with {self._en(风格融合)} influences")
        texture = self._TEXTURE_HINTS.get(制作质感, "")
        if texture:
            extras.append(texture)

        joined = "; ".join(extras).rstrip(".").strip()
        global_text = f"{style['global'].rstrip()} {joined}." if joined else style["global"].rstrip()

        # Vocal Details：配置/声部音区/音色/唱法 + 和声；全部跟随风格时用风格自带文案
        vocal_text = self._compose_vocal(style, 人声配置, 声部音区, 人声音色, 人声唱法, 和声伴唱)
        vocal_fx = self._VOCAL_FX_HINTS.get(人声效果, "")
        if vocal_fx and 人声配置 != "无人声 / Instrumental (No Vocals)":
            vocal_text = f"{vocal_text.rstrip()} {vocal_fx}."

        # Arrangement：风格自带分段时间线 + 可选段落结构指令
        arrangement_text = style["arrangement"].rstrip()
        structure = self._STRUCTURE_HINTS.get(段落结构, "")
        if structure:
            arrangement_text = f"{arrangement_text} {structure}."

        caption = (
            f"Global Metadata: {global_text}\n\n"
            f"Vocal Details: {vocal_text}\n\n"
            f"Arrangement: {arrangement_text}"
        )
        return (caption,)
