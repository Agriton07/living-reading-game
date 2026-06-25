import socket as socket_lib
import logging
import threading
import time
from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'livingreading2025'

socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode='threading',
    ping_timeout=60,
    ping_interval=25
)

# ── Configurable theme list ────────────────────────────────────────────────────
THEMES = [
    'Romance', 'Heartbreak', 'Comedy', 'Drama', 'Tragedy',
    'Hope', 'Nostalgia', 'Mystery', 'Friendship', 'Loneliness',
    'Joy', 'Anger', 'Surrealism', 'Absurdism', 'Wonder', 'Loss',
]

VALID_PHASES = {'setup', 'waiting', 'theme', 'reading', 'erasing', 'cycle', 'reveal'}
_THEMES_SET  = set(THEMES)   # O(1) lookup

# ── Theme lexicons (English + Spanish) ────────────────────────────────────────
# Each theme has 'positive' words (kept = good) and 'negative' words (kept = bad).
# Extend these sets to improve scoring quality for your texts.
THEME_LEXICONS = {
    'Romance': {
        'positive': {
            'love','heart','kiss','tender','warm','soft','dream','touch','hold','together',
            'eternal','soul','beauty','desire','longing','sweet','embrace','passion','intimate',
            'gentle','adore','cherish','devotion','eyes','lips','night','moonlight','glow','bloom',
            # Spanish
            'amor','corazón','beso','dulce','suave','sueño','juntos','alma','belleza','deseo',
            'anhelo','pasión','ternura','ojos','noche','amar','querer','cariño','cuerpo','piel',
        },
        'negative': {
            'hate','cold','war','pain','anger','violence','enemy','ruin','destroy','alone',
            'odio','guerra','dolor','ira','violencia','enemigo','ruina','destruir','soledad',
        },
    },
    'Heartbreak': {
        'positive': {
            'alone','empty','silence','tears','lost','gone','goodbye','broken','cold','shadow',
            'miss','never','end','leave','absence','hurt','wound','forget','sorrow','night','apart',
            'sola','vacío','silencio','lágrimas','perdido','adiós','roto','frío','sombra',
            'extrañar','nunca','fin','ausencia','herida','olvidar','tristeza','noche','lejos',
        },
        'negative': {
            'joy','laugh','together','hope','celebration','smile','happy','warm','bright',
            'alegría','reír','juntos','esperanza','celebración','sonrisa','feliz','calor',
        },
    },
    'Comedy': {
        'positive': {
            'laugh','joke','funny','absurd','silly','ridiculous','strange','unexpected',
            'bizarre','irony','accident','chaos','sudden','confusion','surprise','awkward',
            'reír','broma','gracioso','absurdo','tonto','ridículo','extraño','inesperado',
            'confusión','sorpresa','torpeza','caos',
        },
        'negative': {
            'death','grief','tragedy','sorrow','mourning','tragic','fatal','lament',
            'muerte','duelo','tragedia','pena','luto','trágico','fatal','lamento',
        },
    },
    'Drama': {
        'positive': {
            'conflict','tension','crisis','struggle','confront','reveal','betrayal','secret',
            'truth','lie','power','control','desire','fear','passion','decision','impossible',
            'conflicto','tensión','crisis','lucha','confrontar','revelar','traición','secreto',
            'verdad','mentira','poder','control','miedo','pasión','decisión','imposible',
        },
        'negative': set(),
    },
    'Tragedy': {
        'positive': {
            'death','loss','fall','broken','grief','tears','pain','dark','silence','alone',
            'end','gone','lost','never','cold','hollow','ruin','despair','mourning','fate',
            'inevitable','shadow','collapse','bleed','wound','cry','ashes','final',
            'muerte','pérdida','caída','roto','duelo','lágrimas','dolor','oscuro','silencio',
            'solo','fin','perdido','nunca','frío','vacío','ruina','desesperación','destino',
            'inevitable','sombra','cenizas',
        },
        'negative': {
            'joy','laugh','hope','light','celebrate','happy','smile','love','spring','dance',
            'alegría','reír','esperanza','luz','celebrar','feliz','sonrisa','amor','danza',
        },
    },
    'Hope': {
        'positive': {
            'hope','light','future','dream','rise','new','begin','dawn','sun','tomorrow',
            'believe','possible','forward','grow','open','free','spring','yes','still','again',
            'esperanza','luz','futuro','sueño','amanecer','sol','mañana','creer','posible',
            'adelante','crecer','libre','primavera','todavía','otra','nacer','florecer',
        },
        'negative': {
            'dark','end','lost','impossible','never','dead','close','fall','despair','fail',
            'oscuro','fin','perdido','imposible','nunca','muerto','cerrar','caer','desesperación',
        },
    },
    'Nostalgia': {
        'positive': {
            'memory','remember','past','once','still','long','ago','old','return','familiar',
            'home','yesterday','before','always','echo','ghost','fade','used','childhood','then',
            'recuerdo','recordar','pasado','alguna','todavía','largo','antes','viejo','volver',
            'familiar','hogar','ayer','siempre','eco','fantasma','desvanece','niñez','entonces',
        },
        'negative': {
            'future','new','tomorrow','forward','progress','modern','change','innovation',
            'futuro','nuevo','mañana','adelante','progreso','moderno','cambio',
        },
    },
    'Mystery': {
        'positive': {
            'shadow','secret','unknown','hidden','dark','whisper','strange','silence','night',
            'behind','beneath','unseen','unclear','blur','fog','veil','wonder','uncertain',
            'beneath','underneath','buried','concealed','unspoken','nameless',
            'sombra','secreto','desconocido','oculto','oscuro','susurro','extraño','silencio',
            'noche','detrás','bajo','invisible','difuso','niebla','velo','incierto',
        },
        'negative': {
            'obvious','clear','certain','known','visible','bright','simple','transparent',
            'obvio','claro','cierto','conocido','visible','brillante','simple','transparente',
        },
    },
    'Friendship': {
        'positive': {
            'together','share','trust','loyal','bond','laughter','support','companion','alongside',
            'hand','walk','comfort','care','remember','gift','side','always','return','true',
            'juntos','compartir','confianza','leal','vínculo','risa','apoyo','compañero','al lado',
            'mano','caminar','consuelo','cuidar','recordar','regalo','siempre','volver','fiel',
        },
        'negative': {
            'alone','enemy','betray','abandon','cold','distant','forget','isolate','apart',
            'solo','enemigo','traicionar','abandonar','frío','distante','olvidar','aislar','aparte',
        },
    },
    'Loneliness': {
        'positive': {
            'alone','empty','silence','cold','dark','absent','hollow','echo','nothing','ghost',
            'invisible','forgotten','apart','distance','still','shadow','only','one','nowhere',
            'solo','vacío','silencio','frío','oscuro','ausente','hueco','eco','nada','fantasma',
            'invisible','olvidado','aparte','distancia','quieto','sombra','solo','uno','ningún',
        },
        'negative': {
            'together','crowd','full','warm','laughter','friend','love','hold','welcome',
            'juntos','multitud','lleno','calor','risa','amigo','amor','abrazo','bienvenido',
        },
    },
    'Joy': {
        'positive': {
            'joy','laugh','light','bright','dance','sing','smile','warm','celebrate','free',
            'open','sun','bloom','yes','alive','happy','love','shine','color','spring','play',
            'alegría','reír','luz','brillante','danzar','cantar','sonrisa','calor','celebrar',
            'libre','sol','florecer','sí','vivo','feliz','amor','brillar','color','primavera',
        },
        'negative': {
            'dark','pain','grief','silent','cold','alone','tears','night','die','end',
            'oscuro','dolor','duelo','silencioso','frío','solo','lágrimas','noche','morir',
        },
    },
    'Anger': {
        'positive': {
            'fire','burn','rage','fight','against','break','force','hard','cold','sharp',
            'cut','strike','resist','refuse','never','power','enough','stop','enough','no',
            'fuego','arder','rabia','pelear','contra','romper','fuerza','duro','frío','afilado',
            'cortar','golpear','resistir','rechazar','nunca','poder','basta','parar','no',
        },
        'negative': {
            'soft','gentle','peace','quiet','still','accept','calm','tender','love','forgive',
            'suave','gentil','paz','quieto','tranquilo','aceptar','calma','tierno','amor','perdonar',
        },
    },
    'Surrealism': {
        'positive': {
            'dream','strange','float','between','becomes','transforms','melts','dissolves',
            'impossible','shadow','voice','suddenly','without','beyond','neither','both','never',
            'sueño','extraño','flotar','entre','convierte','transforma','derrite','disuelve',
            'imposible','sombra','voz','de repente','sin','más allá','ni','ambos','jamás',
        },
        'negative': set(),
    },
    'Absurdism': {
        'positive': {
            'nothing','without','because','therefore','still','continues','despite','regardless',
            'anyway','however','nevertheless','yet','despite','although','still','carry','keep',
            'nada','sin','porque','por lo tanto','todavía','continúa','a pesar','sin embargo',
            'de todos modos','aunque','seguir','cargar','mantener','aun así',
        },
        'negative': set(),
    },
    'Wonder': {
        'positive': {
            'wonder','vast','infinite','beyond','light','star','mystery','unknown','beauty',
            'strange','unexpected','discover','more','open','question','infinite','far','deep',
            'asombro','vasto','infinito','más allá','luz','estrella','misterio','desconocido',
            'belleza','extraño','inesperado','descubrir','más','abierto','preguntar','lejos','fondo',
        },
        'negative': {
            'small','boring','plain','obvious','known','closed','certain','limited',
            'pequeño','aburrido','llano','obvio','conocido','cerrado','cierto','limitado',
        },
    },
    'Loss': {
        'positive': {
            'gone','lost','absence','empty','silence','nothing','no longer','without','miss',
            'forget','fade','disappear','shadow','ghost','hollow','leave','never','once','used',
            'ido','perdido','ausencia','vacío','silencio','nada','ya no','sin','extrañar',
            'olvidar','desvanece','desaparecer','sombra','fantasma','hueco','partir','nunca',
        },
        'negative': {
            'found','here','present','alive','full','remember','stay','return','arrive','remain',
            'encontrado','aquí','presente','vivo','lleno','recordar','quedarse','volver','llegar',
        },
    },
}

# ── Thread safety ──────────────────────────────────────────────────────────────
_state_lock = threading.RLock()   # reentrant — safe for nested calls

# ── Global state ───────────────────────────────────────────────────────────────
connected_clients = set()
host_sids         = set()    # all stage SIDs (for reader-count calculation)
active_host_sid   = None     # singleton: ONLY this SID can control the game
submissions       = []
phase             = 'setup'
theme             = None
WORDS             = []
LINE_BREAKS       = []
_cached_podium    = None     # set by background analytics task; cleared on new_round
_cached_stats     = None     # same lifecycle as _cached_podium
_podium_dirty     = True     # True whenever a new submission arrives
_round_id         = 0        # increments on new_round; guards stale background tasks


def is_host():
    """Only the most-recently-connected stage client controls the game."""
    return request.sid == active_host_sid

# ── Text processing ────────────────────────────────────────────────────────────

def parse_text(raw_text):
    global WORDS, LINE_BREAKS
    WORDS = []
    LINE_BREAKS = []
    idx = 0
    for line in raw_text.strip().split('\n'):
        words_in_line = line.strip().split()
        if words_in_line:
            if idx > 0:
                LINE_BREAKS.append(idx)
            WORDS.extend(words_in_line)
            idx += len(words_in_line)


# ── Scoring helpers ────────────────────────────────────────────────────────────

def _clean(word):
    return word.lower().strip('.,!?;:"\'()-—…¿¡«»')


_FUNCTION_WORDS = {
    'a','an','the','of','in','on','at','to','for','and','or','but','nor','so','yet',
    'is','are','was','were','be','been','being','by','from','with','as',
    'it','its','that','this','these','those','i','he','she','we','they','you',
    'me','him','her','us','them','my','his','our','their','your',
    'not','no','do','did','does','have','has','had',
    'will','would','can','could','shall','should','may','might','must',
    'then','than','also','just','more','most','too','very','even','still','only',
    # Spanish
    'el','la','los','las','un','una','unos','unas','de','en','a','por','para',
    'con','sin','sobre','entre','bajo','ante','desde','hasta','hacia','según',
    'y','o','pero','ni','sino','que','si','no','es','son','era','eran','fue',
    'fueron','ser','estar','hay','lo','le','les','se','su','sus','mi','mis',
    'tu','tus','me','te','nos','os','me','te','le','les','ya','así',
    'más','muy','bien','todo','toda','todos','todas','este','esta','estos','estas',
    'ese','esa','esos','esas','aquel','aquella','aquellos','aquellas',
}


def _compute_theme_alignment(kept_words_clean, current_theme):
    """Score 0-100: how well kept words match the chosen theme."""
    if not current_theme or current_theme not in THEME_LEXICONS:
        return 50  # neutral when no theme

    if not kept_words_clean:
        return 0

    lexicon  = THEME_LEXICONS[current_theme]
    positive = lexicon.get('positive', set())
    negative = lexicon.get('negative', set())

    pos_hits = sum(1 for w in kept_words_clean if w in positive)
    neg_hits = sum(1 for w in kept_words_clean if w in negative)

    n = len(kept_words_clean)
    # Each positive word: +2 points above 50 baseline; each negative: -1 point
    raw = (pos_hits * 2 - neg_hits) / n * 50
    return max(0, min(100, 50 + raw))


def _compute_coherence(erased_set, line_breaks_set):
    """Score 0-100: how grammatically connected the kept text is."""
    n = len(WORDS)
    if n == 0:
        return 0

    kept_flags = [i not in erased_set for i in range(n)]
    if not any(kept_flags):
        return 0

    # Average consecutive run length of kept words
    runs, run = [], 0
    for kept in kept_flags:
        if kept:
            run += 1
        elif run:
            runs.append(run)
            run = 0
    if run:
        runs.append(run)

    avg_run     = sum(runs) / len(runs) if runs else 0
    run_score   = min(100, avg_run * 28)   # avg run ≥ 3.6 → 100

    # % of lines that retain ≥ 2 words
    lines, cur = [], []
    for i in range(n):
        if i in line_breaks_set and cur:
            lines.append(cur)
            cur = []
        cur.append(kept_flags[i])
    if cur:
        lines.append(cur)

    good_lines  = sum(1 for ln in lines if sum(ln) >= 2)
    line_score  = (good_lines / len(lines) * 100) if lines else 100

    return run_score * 0.6 + line_score * 0.4


def _compute_readability(erased_set, line_breaks_set):
    """Score 0-100: natural reading flow of the kept text."""
    n = len(WORDS)
    if n == 0:
        return 0

    kept_count = sum(1 for i in range(n) if i not in erased_set)
    if kept_count == 0:
        return 0

    kept_rate = kept_count / n
    if kept_rate < 0.08:
        return 10   # too sparse
    if kept_rate > 0.95:
        return 40   # almost nothing removed — not a real transformation

    lines, cur = [], []
    for i in range(n):
        if i in line_breaks_set and cur:
            lines.append(cur)
            cur = []
        cur.append(i not in erased_set)
    if cur:
        lines.append(cur)

    non_empty    = [ln for ln in lines if any(ln)]
    if not non_empty:
        return 0

    # Average words per non-empty line (target 2-7)
    avg_wpl      = sum(sum(ln) for ln in non_empty) / len(non_empty)
    density      = min(100, avg_wpl * 18)          # 5.5 words/line → 100

    empty_ratio  = len(non_empty) / len(lines)     # penalise leaving blank lines
    return density * 0.65 + empty_ratio * 100 * 0.35


def _compute_economy(n_erased, n_total):
    """Score 0-100: rewards selective (not minimal, not total) deletion.
    Sweet spot: 25-70% deleted."""
    if n_total == 0:
        return 0
    rate = n_erased / n_total
    if rate < 0.10:
        return 15   # barely any deletion
    if rate > 0.92:
        return 15   # deleted almost everything
    # Triangle peak at 45% deletion
    distance = abs(rate - 0.45)
    return round(max(20, 100 - distance * 160))


def score_submission(erased_indices, current_theme):
    """
    Score a single submission against the chosen theme.

    Returns (total: int, breakdown: dict).
    """
    erased_set   = set(erased_indices)
    n_total      = len(WORDS)
    n_erased     = len(erased_set & set(range(n_total)))

    kept_clean   = [
        _clean(WORDS[i])
        for i in range(n_total)
        if i not in erased_set
    ]

    # Filter out pure function words for theme scoring
    kept_content = [w for w in kept_clean if w and w not in _FUNCTION_WORDS and len(w) > 1]

    line_breaks_set = set(LINE_BREAKS)

    theme_score       = _compute_theme_alignment(kept_content, current_theme)
    coherence_score   = _compute_coherence(erased_set, line_breaks_set)
    readability_score = _compute_readability(erased_set, line_breaks_set)
    economy_score     = _compute_economy(n_erased, n_total)

    total = round(
        theme_score       * 0.50 +
        coherence_score   * 0.25 +
        readability_score * 0.15 +
        economy_score     * 0.10
    )

    return total, {
        'theme_alignment': round(theme_score),
        'coherence':       round(coherence_score),
        'readability':     round(readability_score),
        'economy':         round(economy_score),
        'total':           total,
    }


def find_podium():
    """
    Score every submission and return the top 3, sorted by score descending.
    Tiebreak: fewer deletions wins.
    Returns a list of 0–3 dicts; podium[0] is the winner.
    """
    if not submissions or not WORDS:
        return []

    scored = []
    for sub in submissions:
        erased = list(sub.get('erased', []))
        total, breakdown = score_submission(erased, theme)
        scored.append({
            'name':        sub.get('name', 'Anonymous'),
            'erased':      erased,
            'score':       total,
            'breakdown':   breakdown,
            'kept_count':  len(WORDS) - len(set(erased) & set(range(len(WORDS)))),
            'total_words': len(WORDS),
        })

    scored.sort(key=lambda x: (-x['score'], len(x['erased'])))
    return scored[:3]


# ── Analytics (collective) ────────────────────────────────────────────────────

def compute_stats():
    if not submissions or not WORDS:
        return None

    n             = len(submissions)
    erased_counts = [0] * len(WORDS)
    for sub in submissions:
        for i in sub.get('erased', []):
            if 0 <= i < len(WORDS):
                erased_counts[i] += 1

    total_possible = len(WORDS) * n
    total_kept     = sum(n - c for c in erased_counts)
    survival_rate  = round((total_kept / total_possible) * 100) if total_possible > 0 else 0

    most_idx       = max(range(len(erased_counts)), key=lambda i: erased_counts[i])
    most_word      = WORDS[most_idx] if erased_counts[most_idx] > 0 else '—'
    untouched_word = next((WORDS[i] for i, c in enumerate(erased_counts) if c == 0), '—')

    return {
        'survival_rate':  survival_rate,
        'most_erased':    most_word,
        'untouched':      untouched_word,
        'erasure_counts': erased_counts,
        'total_submissions': n,
    }


# ── Payload builder ────────────────────────────────────────────────────────────

def get_payload(for_sid=None):
    """Lightweight game-state snapshot for phase_update broadcasts.

    Submissions are only included during 'cycle' (word cloud needs them).
    Analytics (podium/winner/stats) are NOT included here — they arrive
    via analytics_update or are injected into the on_connect unicast.
    """
    p = {
        'phase':           phase,
        'theme':           theme,
        'count':           len(submissions),
        'total_connected': max(0, len(connected_clients) - len(host_sids)),
        'words':           WORDS,
        'line_breaks':     LINE_BREAKS,
        'round_id':        _round_id,
        # Full submission list only needed by the word-cloud (cycle phase)
        'submissions': [{'erased': list(s['erased'])} for s in submissions]
                       if phase == 'cycle' else [],
    }
    if for_sid is not None:
        p['has_submitted'] = any(s.get('sid') == for_sid for s in submissions)
    return p


def _compute_analytics_async(round_id):
    """Background task: score submissions, cache results, broadcast analytics_update.

    Runs in a separate thread so set_phase('reveal') returns instantly.
    The 50 ms sleep lets any submissions that were in-flight at the moment
    the host triggered reveal finish processing before we compute the podium.
    """
    global _cached_podium, _cached_stats, _podium_dirty
    time.sleep(0.05)
    with _state_lock:
        if round_id != _round_id:
            return                          # new round started — discard
        if not _podium_dirty and _cached_podium is not None:
            podium = _cached_podium         # cache hit — no recomputation
            stats  = _cached_stats
        else:
            podium         = find_podium()
            stats          = compute_stats()
            _cached_podium = podium
            _cached_stats  = stats
            _podium_dirty  = False
    socketio.emit('analytics_update', {
        'round_id': round_id,
        'podium':   podium,
        'winner':   podium[0] if podium else None,
        'stats':    stats,
    })


def get_local_ip():
    s = socket_lib.socket(socket_lib.AF_INET, socket_lib.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip


# ── Routes ─────────────────────────────────────────────────────────────────────

@app.route('/')
def reader():
    return render_template('reader.html')


@app.route('/stage')
def stage():
    return render_template('stage.html')


# ── Socket events ──────────────────────────────────────────────────────────────

@socketio.on('connect')
def on_connect():
    global active_host_sid
    with _state_lock:
        connected_clients.add(request.sid)
        if request.args.get('role') == 'stage':
            host_sids.add(request.sid)
            active_host_sid = request.sid   # newest stage connection owns control
        payload = get_payload(for_sid=request.sid)
        if phase == 'reveal' and _cached_podium is not None:
            payload['podium'] = _cached_podium
            payload['winner'] = _cached_podium[0] if _cached_podium else None
            payload['stats']  = _cached_stats   # use cache, never recompute on connect
        conn_count = max(0, len(connected_clients) - len(host_sids))
    logger.info(f"Connected: {request.sid} role={request.args.get('role','reader')} active_host={active_host_sid}")
    emit('phase_update', payload)
    socketio.emit('connection_update', {'total_connected': conn_count})


@socketio.on('disconnect')
def on_disconnect():
    global active_host_sid
    with _state_lock:
        connected_clients.discard(request.sid)
        host_sids.discard(request.sid)
        # Only clear the active host if it's THIS sid — prevents a race where
        # the new host connected before the old one disconnected.
        if active_host_sid == request.sid:
            active_host_sid = None
        conn_count = max(0, len(connected_clients) - len(host_sids))
    logger.info(f"Disconnected: {request.sid}.")
    socketio.emit('connection_update', {'total_connected': conn_count})


@socketio.on('set_text')
def on_set_text(data):
    global phase, submissions
    if not is_host():
        return
    if not isinstance(data, dict):
        return
    text = data.get('text', '')
    if not isinstance(text, str) or not text.strip():
        return
    with _state_lock:
        parse_text(text)
        submissions = []
        phase = 'waiting'
    socketio.emit('phase_update', get_payload())


@socketio.on('select_theme')
def on_select_theme(data):
    global theme, phase
    if not is_host():
        return
    if not isinstance(data, dict):
        return
    requested = data.get('theme')
    if requested not in _THEMES_SET:
        return
    with _state_lock:
        theme = requested
        phase = 'reading'
    socketio.emit('phase_update', get_payload())


@socketio.on('submit_erasure')
def on_submit(data):
    global submissions

    # Accept during erasing (normal) or cycle (grace: host may have advanced
    # while a slow client was still submitting).
    if phase not in ('erasing', 'cycle'):
        emit('submit_error', {'reason': 'Submissions are closed for this round.'})
        return
    if not isinstance(data, dict):
        return

    raw = data.get('erased', [])
    if not isinstance(raw, list):
        return

    erased_set = set()
    for item in raw:
        try:
            idx = int(item)
        except (TypeError, ValueError):
            continue
        if 0 <= idx < len(WORDS):
            erased_set.add(idx)

    if len(erased_set) == 0:
        emit('submit_error', {'reason': 'Erase at least one word first.'})
        return

    raw_name = data.get('name', '')
    name = str(raw_name).strip()[:30] if raw_name else 'Anonymous'
    if not name:
        name = 'Anonymous'

    with _state_lock:
        # Dedup by SID: replace any previous submission from this socket
        submissions = [s for s in submissions if s.get('sid') != request.sid]
        submissions.append({'erased': erased_set, 'sid': request.sid, 'name': name})
        global _podium_dirty
        _podium_dirty = True               # podium cache is stale
        count      = len(submissions)
        conn_count = max(0, len(connected_clients) - len(host_sids))
        sub_list   = [{'erased': list(s['erased'])} for s in submissions]

    # Acknowledge to THIS client so it knows the server received the poem
    emit('submit_ok', {'name': name})
    socketio.emit('count_update', {
        'count':           count,
        'total_connected': conn_count,
        'submissions':     sub_list,
    })


@socketio.on('set_phase')
def on_set_phase(data):
    global phase
    if not is_host():
        return
    if not isinstance(data, dict):
        return
    requested = data.get('phase', 'setup')
    if requested not in VALID_PHASES:
        return
    with _state_lock:
        phase         = requested
        current_round = _round_id
        payload       = get_payload()   # lightweight — no podium/stats
    # Emit the phase transition immediately so the UI responds without delay
    socketio.emit('phase_update', payload)
    # For reveal: compute analytics in a background thread (non-blocking)
    if requested == 'reveal':
        socketio.start_background_task(_compute_analytics_async, current_round)


@socketio.on('new_round')
def on_new_round():
    global phase, submissions, WORDS, LINE_BREAKS, theme
    global _cached_podium, _cached_stats, _podium_dirty, _round_id
    if not is_host():
        return
    with _state_lock:
        _round_id     += 1       # invalidates any in-flight background tasks
        phase          = 'setup'
        submissions    = []
        WORDS          = []
        LINE_BREAKS    = []
        theme          = None
        _cached_podium = None
        _cached_stats  = None
        _podium_dirty  = True
    socketio.emit('phase_update', get_payload())


if __name__ == '__main__':
    port     = 5050
    local_ip = get_local_ip()
    print('\n' + '═' * 50)
    print('  LIVING READING — Local Server')
    print('═' * 50)
    print(f'\n  Mobile Readers : http://{local_ip}:{port}/')
    print(f'  Stage View     : http://{local_ip}:{port}/stage\n')
    socketio.run(app, host='0.0.0.0', port=port, debug=False)
