const OPENROUTER_KEY   = 'INSERISCI_QUI_LA_TUA_CHIAVE_OPENROUTER'; // sk-or-v1-...
const OPENROUTER_MODEL = 'meta-llama/llama-3.1-8b-instruct:free';

let currentIndex  = 0;
let slides        = [];
let currentChapter = 1;

// ── Init ──
async function init() {
  const data = await store('activeCarousel');
  if (!data || !data.slides || !data.slides.length) {
    document.getElementById('loading').innerHTML =
      '<p style="color:#555;font-size:14px">Nessun carosello trovato.</p>';
    return;
  }

  slides         = data.slides;
  currentChapter = data.chapter || 1;

  document.getElementById('chapter-badge').textContent       = `Capitolo ${currentChapter}`;
  document.getElementById('btn-next-chapter').textContent    = `✨ Genera Capitolo ${currentChapter + 1}`;

  buildSlides(slides);
  buildDots(slides.length);
  showSlide(0);

  document.getElementById('loading').style.display         = 'none';
  document.getElementById('header').style.display          = 'flex';
  document.getElementById('carousel-wrapper').style.display = 'block';
  document.getElementById('nav-prev').style.display        = 'flex';
  document.getElementById('nav-next').style.display        = 'flex';
  document.getElementById('bottom-bar').style.display      = 'flex';
}

// ── Slide rendering ──
function buildSlides(slidesData) {
  const track = document.getElementById('slides-track');
  track.innerHTML = '';
  slidesData.forEach((s, i) => {
    const el = document.createElement('div');
    el.className = 'slide';
    el.dataset.index = i;
    el.innerHTML = `
      <div class="slide-bg"></div>
      <div class="slide-content">
        <div class="slide-num">SLIDE ${String(i + 1).padStart(2, '0')}</div>
        <span class="slide-emoji">${s.emoji || '📖'}</span>
        <h2 class="slide-title">${esc(s.title)}</h2>
        <div class="slide-body">${formatContent(s.content)}</div>
      </div>`;
    track.appendChild(el);
  });
}

function buildDots(count) {
  const dotsEl = document.getElementById('dots');
  dotsEl.innerHTML = '';
  // Show max 12 dots; beyond that show only a counter (dots get too small)
  if (count > 12) return;
  for (let i = 0; i < count; i++) {
    const d = document.createElement('div');
    d.className = 'dot';
    d.onclick = () => showSlide(i);
    dotsEl.appendChild(d);
  }
}

function showSlide(index) {
  currentIndex = Math.max(0, Math.min(index, slides.length - 1));
  document.getElementById('slides-track').style.transform = `translateX(-${currentIndex * 100}%)`;
  document.querySelectorAll('.slide').forEach((s, i) => s.classList.toggle('active', i === currentIndex));
  document.querySelectorAll('.dot').forEach((d, i)   => d.classList.toggle('active', i === currentIndex));
  document.getElementById('slide-counter').textContent = `${currentIndex + 1} / ${slides.length}`;
  document.getElementById('nav-prev').disabled = currentIndex === 0;
  document.getElementById('nav-next').disabled = currentIndex === slides.length - 1;
}

// ── Navigation ──
document.getElementById('nav-prev').addEventListener('click', () => showSlide(currentIndex - 1));
document.getElementById('nav-next').addEventListener('click', () => showSlide(currentIndex + 1));

document.addEventListener('keydown', e => {
  if (e.key === 'ArrowRight' || e.key === 'ArrowDown') showSlide(currentIndex + 1);
  if (e.key === 'ArrowLeft'  || e.key === 'ArrowUp')   showSlide(currentIndex - 1);
  if (e.key === 'Home') showSlide(0);
  if (e.key === 'End')  showSlide(slides.length - 1);
});

// Touch swipe with velocity detection
let touchStartX = 0;
let touchStartY = 0;
let touchStartTime = 0;
document.addEventListener('touchstart', e => {
  touchStartX = e.touches[0].clientX;
  touchStartY = e.touches[0].clientY;
  touchStartTime = Date.now();
}, { passive: true });
document.addEventListener('touchend', e => {
  const dx = e.changedTouches[0].clientX - touchStartX;
  const dy = e.changedTouches[0].clientY - touchStartY;
  const dt = Date.now() - touchStartTime;
  // Only horizontal swipes, ignore vertical scrolls
  if (Math.abs(dx) > Math.abs(dy) && (Math.abs(dx) > 40 || (Math.abs(dx) > 20 && dt < 250))) {
    showSlide(currentIndex + (dx < 0 ? 1 : -1));
    hideSwipeHint();
  }
}, { passive: true });

function hideSwipeHint() {
  const hint = document.getElementById('swipe-hint');
  if (hint) hint.classList.add('hidden');
}

// ── Generate next chapter ──
document.getElementById('btn-next-chapter').addEventListener('click', handleGenerateNext);

async function handleGenerateNext() {
  const nextChapter = currentChapter + 1;
  const btn = document.getElementById('btn-next-chapter');
  btn.disabled = true;

  // Clear previous response state
  await new Promise(r => chrome.storage.local.remove('_responseState', r));

  try {
    const tabs = await chrome.tabs.query({ url: ['https://chat.openai.com/*', 'https://chatgpt.com/*'] });
    if (!tabs.length) {
      showToast('Apri ChatGPT in una scheda e riprova.');
      btn.disabled = false;
      return;
    }
    const tabId = tabs[0].id;

    setGenStep('Invio a ChatGPT...', `Capitolo ${nextChapter}`);
    showOverlay(true);

    const sendResult = await sendToTab(tabId, {
      action: 'sendPrompt',
      prompt: buildPrompt(nextChapter),
    });
    if (!sendResult.success) throw new Error(sendResult.error || 'Errore invio prompt');

    setGenStep('ChatGPT sta scrivendo...', 'attendi la risposta completa');

    // Poll chrome.storage — survives tab switches on mobile
    const rawText = await pollUntilDone();

    setGenStep('Strutturando le slide...', 'analisi con AI');
    const newSlides = await parseSlidesWithAI(rawText, nextChapter);
    if (!newSlides.length) throw new Error('Nessuna slide estratta. Riprova.');

    const state = await store(null);
    const carousels = state.carousels || [];
    const newCarousel = { chapter: nextChapter, slides: newSlides, rawText, createdAt: Date.now() };
    carousels.push(newCarousel);
    await storeSet({ carousels, chapter: nextChapter + 1, activeCarousel: newCarousel });

    currentChapter = nextChapter;
    slides = newSlides;
    document.getElementById('chapter-badge').textContent    = `Capitolo ${currentChapter}`;
    document.getElementById('btn-next-chapter').textContent = `✨ Genera Capitolo ${currentChapter + 1}`;
    buildSlides(slides);
    buildDots(slides.length);
    showSlide(0);
    showOverlay(false);
    btn.disabled = false;

  } catch (err) {
    showOverlay(false);
    showToast(err.message);
    btn.disabled = false;
  }
}

// ── Poll from chrome.storage — no tab-message required ──
function pollUntilDone() {
  return new Promise((resolve, reject) => {
    const deadline = Date.now() + 3 * 60 * 1000;
    function tick() {
      if (Date.now() > deadline) { reject(new Error('Timeout: ChatGPT non ha risposto in tempo')); return; }
      chrome.storage.local.get('_responseState', data => {
        const r = data._responseState;
        if (!r) { setTimeout(tick, 1500); return; }
        if (r.done && r.text) { resolve(r.text); return; }
        const info = r.generating
          ? `in generazione… ${r.textLength || 0} car.`
          : `${r.textLength || 0} car., verifica stabilità`;
        setGenStep('ChatGPT sta scrivendo...', info);
        setTimeout(tick, 1500);
      });
    }
    setTimeout(tick, 8000);
  });
}

function sendToTab(tabId, message) {
  return new Promise((resolve, reject) => {
    chrome.tabs.sendMessage(tabId, message, resp => {
      if (chrome.runtime.lastError) {
        chrome.scripting.executeScript({ target: { tabId }, files: ['content.js'] }, () => {
          setTimeout(() => {
            chrome.tabs.sendMessage(tabId, message, resp2 => {
              if (chrome.runtime.lastError) reject(new Error(chrome.runtime.lastError.message));
              else resolve(resp2);
            });
          }, 600);
        });
      } else resolve(resp);
    });
  });
}

// ── OpenRouter slide parsing ──
async function parseSlidesWithAI(rawText, chapter) {
  const local = parseSlides(rawText);
  if (local.length >= 3) return local;

  try {
    const res = await fetch('https://openrouter.ai/api/v1/chat/completions', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${OPENROUTER_KEY}`,
        'Content-Type': 'application/json',
        'HTTP-Referer': 'https://book-carousel-ext',
        'X-Title': 'Book Carousel',
      },
      body: JSON.stringify({
        model: OPENROUTER_MODEL,
        messages: [{
          role: 'user',
          content: `Estrai le slide dal testo seguente e restituisci SOLO un array JSON valido:
[{"emoji":"🔥","title":"Titolo","content":"Testo"}]

Testo:
${rawText.slice(0, 6000)}

Rispondi SOLO con il JSON, nient'altro.`,
        }],
        max_tokens: 2000,
        temperature: 0.2,
      }),
    });
    const data = await res.json();
    const text = data.choices?.[0]?.message?.content || '';
    const m = text.match(/\[[\s\S]*\]/);
    if (m) return JSON.parse(m[0]);
  } catch (e) { console.error('OpenRouter:', e); }

  return local;
}

function parseSlides(text) {
  const slides = [];
  const re = /\[SLIDE\s*(\d+)\]([\s\S]*?)\[\/SLIDE\s*\1\]/gi;
  let m;
  while ((m = re.exec(text)) !== null) {
    const block   = m[2];
    const emoji   = (block.match(/EMOJI:\s*(.+)/i)          || [])[1]?.trim() || '📖';
    const title   = (block.match(/TITOLO:\s*(.+)/i)         || [])[1]?.trim() || '';
    const content = (block.match(/CONTENUTO:\s*([\s\S]+)/i) || [])[1]?.trim() || '';
    if (title) slides.push({ emoji, title, content });
  }
  return slides;
}

function buildPrompt(chapter) {
  return `Perfetto! Ora fai lo stesso per il CAPITOLO ${chapter}: crea un carosello di 8-10 slide engaging con lo stesso formato:

[SLIDE 1]
EMOJI: 🔥
TITOLO: Titolo della slide
CONTENUTO: Testo della slide
[/SLIDE 1]

[SLIDE 2]
...

Usa lo stesso stile divulgativo e coinvolgente. Ogni slide deve essere un hook per la successiva.`;
}

// ── UI helpers ──
function showOverlay(visible) {
  document.getElementById('gen-overlay').classList.toggle('visible', visible);
}
function setGenStep(label, step) {
  document.getElementById('gen-label').textContent = label;
  document.getElementById('gen-step').textContent  = step || '';
}
function showToast(msg) {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.classList.add('visible');
  setTimeout(() => t.classList.remove('visible'), 6000);
}

function formatContent(text) {
  if (!text) return '';
  const lines = text.split('\n').map(l => l.trim()).filter(Boolean);
  const bulletRe = /^[-•*]\s+|^\d+[.)]\s+/;
  if (lines.length > 1 && lines.some(l => bulletRe.test(l)))
    return '<ul>' + lines.map(l => `<li>${esc(l.replace(bulletRe, ''))}</li>`).join('') + '</ul>';
  if (lines.length > 1)
    return lines.map(l => `<p>${esc(l)}</p>`).join('');
  return `<p>${esc(text)}</p>`;
}

function esc(s) {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function store(key) {
  return new Promise(resolve => {
    if (key) chrome.storage.local.get(key, d => resolve(d[key]));
    else chrome.storage.local.get(null, resolve);
  });
}
function storeSet(obj) {
  return new Promise(resolve => chrome.storage.local.set(obj, resolve));
}

init();
