/* GONTOBBO frontend/backend integration bridge. Served from the same FastAPI origin. */
(() => {
  // Keep API calls on FastAPI even when Chrome/VS Code serves this file from
  // file://, localhost:5500, 127.0.0.1:5500, or another local static port.
  // A URL override is supported for LAN/custom ports: ?api=http://HOST:8000
  // or window.GONTOBBO_BACKEND_URL set before this script loads.
  const params = new URLSearchParams(location.search || '');
  const override = params.get('api') || window.GONTOBBO_BACKEND_URL || '';
  const host = location.hostname && location.hostname !== 'null' ? location.hostname : '127.0.0.1';
  const apiHost = host === 'localhost' ? '127.0.0.1' : host;
  const staticFrontend = location.protocol === 'file:' || !location.port || location.port !== '8000';
  const localBackend = `${location.protocol === 'https:' ? 'https' : 'http'}://${apiHost}:8000`;
  const apiOrigin = String(override || (staticFrontend ? localBackend : '')).replace(/\/$/, '');
  window.GONTOBBO_API_ORIGIN = apiOrigin;
  const api = async (path, options = {}) => {
    const res = await fetch(apiOrigin + path, { headers: { 'Content-Type': 'application/json', ...(options.headers || {}) }, ...options });
    const contentType = res.headers.get('content-type') || '';
    if (!contentType.includes('application/json')) {
      throw new Error('Backend API response was not JSON. Start GONTOBBO with start.bat and open http://127.0.0.1:8000/ in Chrome.');
    }
    return res;
  };
  const esc = (value) => String(value ?? '').replace(/[&<>"']/g, (c) => ({ '&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#039;' }[c]));
  const currencyRates = { INR:1, USD:0.0117, GBP:0.0087, AED:0.0430, SGD:0.0151, AUD:0.0178, CAD:0.0160, JPY:1.73, CNY:0.0845, EUR:0.0100, CHF:0.0092, THB:0.395, MYR:0.0500, IDR:184.0, NPR:1.58 };
  const currencySymbols = { INR:'₹', USD:'$', GBP:'£', AED:'د.إ', SGD:'S$', AUD:'A$', CAD:'C$', JPY:'¥', CNY:'¥', EUR:'€', CHF:'CHF ', THB:'฿', MYR:'RM ', IDR:'Rp ', NPR:'रू ' };
  const selectedCurrency = () => document.getElementById('currencySelect')?.value || 'INR';
  const money = (value) => { const code=selectedCurrency(), amount=Number(value || 0)*Number(currencyRates[code] || 1), decimals=(code==='JPY'||code==='IDR')?0:2; return `${currencySymbols[code] || code}${amount.toLocaleString('en-US',{minimumFractionDigits:decimals,maximumFractionDigits:decimals})}`; };
  const liveLabels = { en:{compare:'Compare',rating:'rating',stars:'stars',night:'/ night',featured:'Featured stay'}, bn:{compare:'তুলনা',rating:'রেটিং',stars:'তারকা',night:'/ রাত',featured:'নির্বাচিত থাকা'}, hi:{compare:'तुलना',rating:'रेटिंग',stars:'सितारे',night:'/ रात',featured:'चयनित ठहराव'}, ta:{compare:'ஒப்பிடுக',rating:'மதிப்பீடு',stars:'நட்சத்திரங்கள்',night:'/ இரவு',featured:'தேர்ந்தெடுக்கப்பட்டது'}, te:{compare:'పోల్చండి',rating:'రేటింగ్',stars:'నక్షత్రాలు',night:'/ రాత్రి',featured:'ఎంచుకున్న బస'}, mr:{compare:'तुलना',rating:'रेटिंग',stars:'तारे',night:'/ रात्र',featured:'निवडलेला मुक्काम'} };
  const label = key => (liveLabels[document.getElementById('languageSelect')?.value || 'en'] || liveLabels.en)[key] || liveLabels.en[key];
  const showStatus = (container, message, error = false) => {
    container.hidden = false;
    container.innerHTML = `<div style="padding:18px;border-radius:16px;background:${error ? '#fff1f1' : '#f5f2ff'};color:${error ? '#a22' : '#4b3a8e'}">${esc(message)}</div>`;
  };
  let allHotels = [];
  let selectedHotels = [];

  function selectedFilter(id) { return document.getElementById(id)?.value || 'all'; }
  function filteredHotels() {
    const budget = selectedFilter('filterBudget');
    const stars = Number(selectedFilter('filterStars')) || 0;
    const comfort = selectedFilter('filterComfort');
    const rating = Number(selectedFilter('filterGuestRating')) || 0;
    const type = selectedFilter('filterType');
    const meal = selectedFilter('filterMeal');
    const facility = selectedFilter('filterFacility');
    const sort = selectedFilter('filterSort');
    let list = allHotels.filter(h => {
      if (!(Number(h.price) > 0)) return false;
      const price = Number(h.price || 0);
      const inBudget = budget === 'all' || (budget === '0-2500' && price < 2500) || (budget === '2500-5000' && price >= 2500 && price < 5000) || (budget === '5000-8000' && price >= 5000 && price < 8000) || (budget === '8000+' && price >= 8000);
      return inBudget && (!stars || Number(h.stars || 0) >= stars) && (comfort === 'all' || h.comfort === comfort) && (!rating || Number(h.rating || 0) >= rating) && (type === 'all' || h.type === type) && (meal === 'all' || h.meal === meal) && (facility === 'all' || (h.facilities || []).includes(facility));
    });
    if (sort === 'priceLow') list.sort((a,b) => Number(a.price || 0) - Number(b.price || 0));
    if (sort === 'priceHigh') list.sort((a,b) => Number(b.price || 0) - Number(a.price || 0));
    if (sort === 'stars') list.sort((a,b) => Number(b.stars || 0) - Number(a.stars || 0));
    if (sort === 'rating') list.sort((a,b) => Number(b.rating || 0) - Number(a.rating || 0));
    return list;
  }
  function syncCompareCount() {
    const el = document.getElementById('compareCount');
    if (el) el.textContent = `${selectedHotels.length} / 2 selected`;
    const btn = document.getElementById('compareOpenBtn'); if (btn) btn.disabled = selectedHotels.length !== 2;
  }
  function toggleCompare(id, checked) {
    if (checked && selectedHotels.length >= 2) { const box = document.querySelector(`[data-hotel-id="${CSS.escape(id)}"] .live-compare-toggle`); if (box) box.checked = false; return; }
    selectedHotels = checked ? [...selectedHotels, id] : selectedHotels.filter(x => x !== id);
    syncCompareCount();
  }
  function renderCompare() {
    const wrap = document.getElementById('compareTableWrap');
    const modal = document.getElementById('hotelCompareModal');
    if (!wrap || selectedHotels.length !== 2) return;
    const rows = selectedHotels.map(id => allHotels.find(h => h.id === id)).filter(Boolean);
    wrap.innerHTML = `<div class="live-compare-grid">${rows.map(h => `<div class="saved-card" style="padding:18px"><img src="${esc(h.img)}" alt="${esc(h.name)}" style="width:100%;height:150px;object-fit:cover;border-radius:12px"><h3>${esc(h.name)}</h3><p><b>Price:</b> ${money(h.price)} ${esc(label('night'))}</p><p><b>${esc(label('rating'))}:</b> ${esc(h.rating)} (${esc(h.reviews)} reviews)</p><p><b>${esc(label('stars'))}:</b> ${esc(h.stars)}</p><p><b>Comfort:</b> ${esc(h.comfort)}</p><p><b>Meal:</b> ${esc(h.meal)}</p><p><b>Facilities:</b> ${esc((h.facilities || []).join(', '))}</p></div>`).join('')}</div>`;
    // The uploaded page styles this modal with the `open` class (not `show`).
    modal.classList.add('open'); modal.classList.remove('show'); modal.setAttribute('aria-hidden', 'false'); document.body.style.overflow = 'hidden';
  }
  function renderHotels() {
    const grid = document.getElementById('hotelGrid');
    const list = filteredHotels();
    if (!list.length) return showStatus(grid, 'No hotels match these filters. Try changing one or two filters.');
    grid.innerHTML = list.map(h => `<article class="hotel-card live-hotel-card" data-hotel-id="${esc(h.id)}" style="overflow:hidden"><img class="live-hotel-thumb" src="${esc(h.thumbnail || h.img)}" alt="${esc(h.name)}" width="640" height="360" loading="lazy" decoding="async" onerror="this.onerror=null;this.src='${esc(h.img)}'"><div style="padding:16px"><div style="display:flex;justify-content:space-between;gap:8px;align-items:center"><h3>${esc(h.name)}</h3><label style="white-space:nowrap;font-size:12px"><input class="live-compare-toggle" type="checkbox" ${selectedHotels.includes(h.id) ? 'checked' : ''} aria-label="${esc(label('compare'))} ${esc(h.name)}"> ${esc(label('compare'))}</label></div><p>${esc(h.type || 'Hotel')} · ${esc(h.rating || '—')} ${esc(label('rating'))} · ${esc(h.stars || '—')} ${esc(label('stars'))}</p><strong>${money(h.price)} ${esc(label('night'))}</strong><p>${esc((h.facilities || []).slice(0, 3).join(' · '))}</p><div class="live-hotel-actions"><button type="button" class="live-favorite-btn">${window.gontobboIsFavorite?.(h.id) ? '♥ Saved' : '♡ Save'}</button><button type="button" class="live-view-btn">View details</button></div></div></article>`).join('');
    grid.querySelectorAll('.live-compare-toggle').forEach(box => box.addEventListener('change', e => toggleCompare(e.target.closest('[data-hotel-id]').dataset.hotelId, e.target.checked)));
    grid.querySelectorAll('.live-favorite-btn').forEach(button => button.addEventListener('click', e => {
      e.stopPropagation(); const card=e.currentTarget.closest('[data-hotel-id]'), hotel=allHotels.find(h => h.id === card?.dataset.hotelId);
      if (hotel && window.gontobboToggleFavorite) { window.gontobboToggleFavorite(hotel.id, hotel); renderHotels(); }
    }));
    grid.querySelectorAll('.live-view-btn').forEach(button => button.addEventListener('click', e => {
      e.stopPropagation(); const card=e.currentTarget.closest('[data-hotel-id]'), hotel=allHotels.find(h => h.id === card?.dataset.hotelId);
      if (hotel) openHotelDetails(hotel);
    }));
    syncCompareCount();
  }
  function wireHotelControls() {
    ['filterBudget','filterStars','filterComfort','filterGuestRating','filterType','filterMeal','filterSort','filterFacility'].forEach(id => document.getElementById(id)?.addEventListener('change', renderHotels));
    document.getElementById('clearHotelFilters')?.addEventListener('click', () => { ['filterBudget','filterStars','filterComfort','filterGuestRating','filterType','filterMeal','filterSort','filterFacility'].forEach(id => { const el = document.getElementById(id); if (el) el.value = id === 'filterSort' ? 'recommended' : 'all'; }); renderHotels(); });
    // Capture the click before the original demo comparison handler. The
    // original handler still exists in the uploaded HTML and otherwise wins
    // the event, leaving the live API cards out of the comparison modal.
    document.getElementById('compareOpenBtn')?.addEventListener('click', e => { e.preventDefault(); e.stopImmediatePropagation(); if (selectedHotels.length === 2) renderCompare(); }, true);
    document.getElementById('compareClose')?.addEventListener('click', () => { const m = document.getElementById('hotelCompareModal'); m?.classList.remove('open', 'show'); m?.setAttribute('aria-hidden', 'true'); document.body.style.overflow = ''; });
  }

  function exploreHotelCity(city) {
    const stateByCity = { Goa:'Goa', Mumbai:'Maharashtra', Pune:'Maharashtra', Jaipur:'Rajasthan', Udaipur:'Rajasthan', Kolkata:'West Bengal', Chennai:'Tamil Nadu', Bengaluru:'Karnataka', Delhi:'Delhi (NCT)', Guwahati:'Assam', Darjeeling:'West Bengal', Hyderabad:'Telangana' };
    const destination = document.getElementById('destination');
    const citySelect = document.getElementById('city');
    const state = stateByCity[city] || 'Goa';
    if (!destination || !citySelect) return;
    destination.value = state;
    destination.dispatchEvent(new Event('change', { bubbles: true }));
    const now = new Date();
    const formatDate = d => { const y=d.getFullYear(), m=String(d.getMonth()+1).padStart(2,'0'), day=String(d.getDate()).padStart(2,'0'); return `${y}-${m}-${day}`; };
    const checkIn = document.getElementById('homeCheckIn'), checkOut = document.getElementById('homeCheckOut');
    if (checkIn && !checkIn.value) { const d=new Date(now); d.setDate(d.getDate()+1); checkIn.value=formatDate(d); checkIn.dispatchEvent(new Event('change',{bubbles:true})); }
    if (checkOut && !checkOut.value) { const d=new Date(now); d.setDate(d.getDate()+3); checkOut.value=formatDate(d); checkOut.dispatchEvent(new Event('change',{bubbles:true})); }
    setTimeout(() => {
      const option = [...citySelect.options].find(o => o.value.toLowerCase() === city.toLowerCase() || o.textContent.trim().toLowerCase() === city.toLowerCase());
      if (option) { citySelect.value = option.value; citySelect.dispatchEvent(new Event('change',{bubbles:true})); document.getElementById('search')?.scrollIntoView({ behavior:'smooth', block:'center' }); document.getElementById('searchHotelsBtn')?.click(); }
    }, 80);
  }

  function exploreFeaturedHotel(button) {
    const card = button.closest('.deal-card, .rated-card');
    if (!card) return exploreHotelCity(button.dataset.searchCity || 'Goa');
    const name = card.querySelector('h3')?.textContent?.trim() || 'Featured hotel';
    const city = button.dataset.searchCity || card.dataset.city || (card.querySelector('p')?.textContent?.match(/📍\s*([^,]+)/)?.[1] || '');
    const image = card.querySelector('.deal-banner, .rated-photo')?.style.backgroundImage?.match(/url\(["']?(.*?)["']?\)/)?.[1] || card.querySelector('img')?.src || '';
    const namedHotelPhotos = {
      'Alila Diwa Goa Getaway': ['https://files.manuscdn.com/search-media/310519663992011267/lLYFQtDaaFxj29vuVBrQPd/mDuWsLC3J64A9aXeZXYX9d.jpg','https://files.manuscdn.com/search-media/310519663992011267/lLYFQtDaaFxj29vuVBrQPd/dkzdQM6ZkSGeG6Asux4429.jpg','https://files.manuscdn.com/search-media/310519663992011267/lLYFQtDaaFxj29vuVBrQPd/zJaGp8p9ywDDKPNSAoMtv5.jpg'],
      'Rambagh Palace, Jaipur': ['https://files.manuscdn.com/search-media/310519663992011267/lLYFQtDaaFxj29vuVBrQPd/m5tk4c53fStu9mANXUEz7P.jpg','https://files.manuscdn.com/search-media/310519663992011267/lLYFQtDaaFxj29vuVBrQPd/ownJtzEXbzJy2T3vup4MpK.jpg','https://files.manuscdn.com/search-media/310519663992011267/lLYFQtDaaFxj29vuVBrQPd/Cp2PoDisDwmAnsJ9XMWhRE.jpg'],
      'The Oberoi Grand, Kolkata': ['https://files.manuscdn.com/search-media/310519663992011267/lLYFQtDaaFxj29vuVBrQPd/auriMYSWdRcmXdW2SJ46fZ.jpg'],
      'Taj Lands End, Mumbai': ['https://files.manuscdn.com/search-media/310519663992011267/lLYFQtDaaFxj29vuVBrQPd/mhEh65tUnynmxs8DqzC9Ni.webp','https://files.manuscdn.com/search-media/310519663992011267/lLYFQtDaaFxj29vuVBrQPd/U2UMrMKDSrGgrqe8ZTGdUQ.jpg','https://files.manuscdn.com/search-media/310519663992011267/lLYFQtDaaFxj29vuVBrQPd/R3VwaU4egkRYdiseddTbjB.jpg']
    };
    const namedHotelCoordinates = {
      'Alila Diwa Goa Getaway': [15.2975, 73.9057],
      'Rambagh Palace, Jaipur': [26.8923, 75.8062],
      'The Oberoi Grand, Kolkata': [22.5604, 88.3526],
      'Taj Lands End, Mumbai': [19.0427, 72.8197]
    };
    const coordinates = namedHotelCoordinates[name] || null;
    const priceNode = card.querySelector('[data-inr]');
    const ratingText = card.querySelector('.stars span')?.textContent?.trim() || '0';
    allHotels = [{
      id: `featured-${name.toLowerCase().replace(/[^a-z0-9]+/g, '-')}`, name, city, state: '', img: image,
      price: Number(priceNode?.dataset.inr || 0), currency: 'INR', total_price: 0, stars: 5,
      rating: Number(ratingText) || 0, reviews: 0, comfort: 'Premium', type: 'Hotel',
      meal: 'Room Only', facilities: ['Featured stay'], images: namedHotelPhotos[name] || [image], latitude: coordinates?.[0], longitude: coordinates?.[1]
    }];
    selectedHotels = [];
    document.getElementById('hotelResults')?.classList.add('show');
    const summary = document.getElementById('resultsSummary');
    if (summary) summary.textContent = `Showing the selected featured stay: ${name}`;
    wireHotelControls(); renderHotels();
    openHotelDetails(allHotels[0]);
  }

  const famousPlaces = {
    Guwahati: [['Kamakhya Temple','Sacred hilltop temple and city landmark','https://images.unsplash.com/photo-1609766857041-ed402ea8069a?auto=format&fit=crop&w=900&q=85'],['Umananda Island','Peaceful river island in the Brahmaputra','https://images.unsplash.com/photo-1548013146-72479768bada?auto=format&fit=crop&w=900&q=85'],['Assam State Museum','History, art and culture of Assam','https://images.unsplash.com/photo-1564399579883-451a5d44ec08?auto=format&fit=crop&w=900&q=85'],['Deepor Beel','Birdwatching and sunset by the wetland','https://images.unsplash.com/photo-1500534623283-312aade485b7?auto=format&fit=crop&w=900&q=85']],
    Goa: [['Baga Beach','Golden sands, cafés and sunset views','https://images.unsplash.com/photo-1512343879784-a960bf40e7f2?auto=format&fit=crop&w=900&q=85'],['Fort Aguada','Historic fort overlooking the Arabian Sea','https://images.unsplash.com/photo-1596402184320-417e7178b2cd?auto=format&fit=crop&w=900&q=85'],['Dudhsagar Falls','Majestic waterfall in the Western Ghats','https://images.unsplash.com/photo-1433086966358-54859d0ed716?auto=format&fit=crop&w=900&q=85'],['Basilica of Bom Jesus','Baroque heritage church in Old Goa','https://images.unsplash.com/photo-1548013146-72479768bada?auto=format&fit=crop&w=900&q=85']],
    Jaipur: [['Amber Fort','Hilltop palace with grand courtyards','https://images.unsplash.com/photo-1599661046289-e31897846e41?auto=format&fit=crop&w=900&q=85'],['Hawa Mahal','The iconic Palace of Winds','https://images.unsplash.com/photo-1477587458883-47145ed94245?auto=format&fit=crop&w=900&q=85'],['City Palace','Royal heritage in the heart of Jaipur','https://images.unsplash.com/photo-1603262110263-fb0112e7cc33?auto=format&fit=crop&w=900&q=85'],['Jantar Mantar','Historic astronomical observatory','https://images.unsplash.com/photo-1539650116574-75c0c6d73f6e?auto=format&fit=crop&w=900&q=85']],
    Kolkata: [['Victoria Memorial','Marble monument surrounded by gardens','https://images.unsplash.com/photo-1558431382-27e303142255?auto=format&fit=crop&w=900&q=85'],['Howrah Bridge','Kolkata’s famous steel bridge','https://images.unsplash.com/photo-1558431382-27e303142255?auto=format&fit=crop&w=900&q=85'],['Indian Museum','One of India’s oldest museums','https://images.unsplash.com/photo-1564399579883-451a5d44ec08?auto=format&fit=crop&w=900&q=85'],['Prinsep Ghat','Riverside promenade and sunset spot','https://images.unsplash.com/photo-1500534623283-312aade485b7?auto=format&fit=crop&w=900&q=85']],
    Mumbai: [['Gateway of India','Waterfront monument and city icon','https://images.unsplash.com/photo-1570168007204-dfb528c6958f?auto=format&fit=crop&w=900&q=85'],['Marine Drive','The Queen’s Necklace by the sea','https://images.unsplash.com/photo-1595658658481-d53d3f999875?auto=format&fit=crop&w=900&q=85'],['Elephanta Caves','Rock-cut heritage island caves','https://images.unsplash.com/photo-1595658658481-d53d3f999875?auto=format&fit=crop&w=900&q=85'],['Chhatrapati Shivaji Terminus','Gothic revival railway landmark','https://images.unsplash.com/photo-1570168007204-dfb528c6958f?auto=format&fit=crop&w=900&q=85']],
    Delhi: [['India Gate','National war memorial and broad avenue','https://images.unsplash.com/photo-1587474260584-136574528ed5?auto=format&fit=crop&w=900&q=85'],['Red Fort','Mughal-era red sandstone fort','https://images.unsplash.com/photo-1585506942812-e72b29cef752?auto=format&fit=crop&w=900&q=85'],['Qutub Minar','UNESCO-listed historic minaret','https://images.unsplash.com/photo-1585135497273-1a86b09fe70e?auto=format&fit=crop&w=900&q=85'],['Lotus Temple','Peaceful lotus-shaped house of worship','https://images.unsplash.com/photo-1564507592333-c60657eea523?auto=format&fit=crop&w=900&q=85']],
    Chennai: [['Marina Beach','Long urban beach and sunrise walk','https://images.unsplash.com/photo-1507525428034-b723cf961d3e?auto=format&fit=crop&w=900&q=85'],['Kapaleeshwarar Temple','Colourful Dravidian temple landmark','https://images.unsplash.com/photo-1609766857041-ed402ea8069a?auto=format&fit=crop&w=900&q=85'],['Fort St George','Colonial fort and museum complex','https://images.unsplash.com/photo-1539650116574-75c0c6d73f6e?auto=format&fit=crop&w=900&q=85'],['Mahabalipuram','Shore temples and ancient stone carvings','https://images.unsplash.com/photo-1548013146-72479768bada?auto=format&fit=crop&w=900&q=85']],
    Pune: [['Shaniwar Wada','Historic fort and Peshwa-era landmark','https://images.unsplash.com/photo-1539650116574-75c0c6d73f6e?auto=format&fit=crop&w=900&q=85'],['Aga Khan Palace','Heritage palace and memorial','https://images.unsplash.com/photo-1548013146-72479768bada?auto=format&fit=crop&w=900&q=85'],['Sinhagad Fort','Hilltop fort and scenic getaway','https://images.unsplash.com/photo-1500534623283-312aade485b7?auto=format&fit=crop&w=900&q=85'],['Lal Mahal','Historic red palace in the old city','https://images.unsplash.com/photo-1539650116574-75c0c6d73f6e?auto=format&fit=crop&w=900&q=85']],
    Bengaluru: [['Lalbagh Botanical Garden','Historic garden and glasshouse','https://images.unsplash.com/photo-1441974231531-c6227db76b6e?auto=format&fit=crop&w=900&q=85'],['Bengaluru Palace','Royal Tudor-style heritage landmark','https://images.unsplash.com/photo-1539650116574-75c0c6d73f6e?auto=format&fit=crop&w=900&q=85'],['Cubbon Park','Green escape in the city centre','https://images.unsplash.com/photo-1441974231531-c6227db76b6e?auto=format&fit=crop&w=900&q=85'],['Vidhana Soudha','Iconic state legislature building','https://images.unsplash.com/photo-1477959858617-67f85cf4f1df?auto=format&fit=crop&w=900&q=85']],
    Darjeeling: [['Tiger Hill','Famous sunrise viewpoint over the Himalayas','https://images.unsplash.com/photo-1544735716-392fe2489ffa?auto=format&fit=crop&w=900&q=85'],['Batasia Loop','Scenic mountain railway viewpoint','https://images.unsplash.com/photo-1500534623283-312aade485b7?auto=format&fit=crop&w=900&q=85'],['Peace Pagoda','Panoramic hilltop Buddhist landmark','https://images.unsplash.com/photo-1548013146-72479768bada?auto=format&fit=crop&w=900&q=85'],['Happy Valley Tea Estate','Tea gardens and local experience','https://images.unsplash.com/photo-1500534623283-312aade485b7?auto=format&fit=crop&w=900&q=85']],
    Udaipur: [['City Palace','Royal palace overlooking Lake Pichola','https://images.unsplash.com/photo-1603262110263-fb0112e7cc33?auto=format&fit=crop&w=900&q=85'],['Lake Pichola','Boat rides and sunset views','https://images.unsplash.com/photo-1564501049412-61c2a3083791?auto=format&fit=crop&w=900&q=85'],['Sajjangarh Palace','Monsoon Palace hilltop panorama','https://images.unsplash.com/photo-1539650116574-75c0c6d73f6e?auto=format&fit=crop&w=900&q=85'],['Jagdish Temple','Historic temple in the old city','https://images.unsplash.com/photo-1548013146-72479768bada?auto=format&fit=crop&w=900&q=85']]
  };
  const placeFallback = [['City Centre','Popular local sights and neighbourhoods','https://images.unsplash.com/photo-1477959858617-67f85cf4f1df?auto=format&fit=crop&w=900&q=85'],['Heritage Area','History, architecture and local culture','https://images.unsplash.com/photo-1539650116574-75c0c6d73f6e?auto=format&fit=crop&w=900&q=85'],['Central Park','Relaxing green space for a city break','https://images.unsplash.com/photo-1441974231531-c6227db76b6e?auto=format&fit=crop&w=900&q=85'],['Local Market','Food, shopping and local life','https://images.unsplash.com/photo-1488459716781-31db52582fe9?auto=format&fit=crop&w=900&q=85']];
  const expandedPlaces = {
    Hyderabad: [['Charminar','Iconic four-minaret monument'],['Golconda Fort','Historic hilltop fort'],['Salar Jung Museum','World-class art and antiques'],['Hussain Sagar Lake','Lake and Buddha statue'],['Chowmahalla Palace','Nizam-era palace complex'],['Qutb Shahi Tombs','Royal tombs and gardens'],['Ramoji Film City','Film studio and theme park'],['Birla Mandir','Hilltop marble temple']],
    Ahmedabad: [['Sabarmati Ashram','Gandhian heritage site'],['Adalaj Stepwell','Historic stepwell architecture'],['Kankaria Lake','Lakeside recreation and gardens'],['Sidi Saiyyed Mosque','Famous stone latticework'],['Science City','Interactive science attractions'],['Jama Masjid','Historic mosque in the old city'],['Sabarmati Riverfront','Riverside promenade'],['Law Garden','Handicrafts and local food']],
    Agra: [['Taj Mahal','World-famous marble monument'],['Agra Fort','Mughal fort and palace'],['Fatehpur Sikri','Historic imperial city'],['Mehtab Bagh','Taj Mahal sunset garden'],['Itmad-ud-Daulah','Riverside Mughal tomb'],['Akbar’s Tomb','Grand mausoleum at Sikandra'],['Agra Bear Rescue','Wildlife conservation centre'],['Kinari Bazaar','Local market and crafts']],
    Varanasi: [['Kashi Vishwanath Temple','Sacred temple in the old city'],['Dashashwamedh Ghat','Ganga Aarti and riverside steps'],['Sarnath','Buddhist heritage site'],['Manikarnika Ghat','Historic cremation ghat'],['Assi Ghat','Sunrise and cultural walks'],['Ramnagar Fort','Riverside royal fort'],['Banaras Hindu University','Historic university campus'],['Tulsi Manas Temple','Cultural temple and museum']],
    Kochi: [['Fort Kochi','Colonial quarter and art scene'],['Chinese Fishing Nets','Historic waterfront landmark'],['Mattancherry Palace','Dutch Palace museum'],['Jewish Town','Heritage streets and synagogue'],['Marine Drive','Harbourfront promenade'],['Hill Palace Museum','Royal heritage museum'],['Kerala Folklore Museum','Traditional art and culture'],['Cherai Beach','Coastal escape']],
    Jodhpur: [['Mehrangarh Fort','Massive hilltop fort'],['Jaswant Thada','White marble memorial'],['Umaid Bhawan Palace','Royal palace and museum'],['Blue City','Old town blue houses'],['Mandore Gardens','Historic gardens and temples'],['Clock Tower Market','Local bazaar and food'],['Rao Jodha Desert Park','Native desert landscape'],['Kaylana Lake','Sunset lake views']],
    Mysuru: [['Mysore Palace','Illuminated royal palace'],['Chamundi Hill','Temple and city panorama'],['Brindavan Gardens','Musical fountains and gardens'],['St Philomena’s Cathedral','Gothic cathedral'],['Devaraja Market','Historic local market'],['Karanji Lake','Urban nature reserve'],['Jaganmohan Palace','Art gallery and heritage'],['Railway Museum','Historic locomotives']],
    Visakhapatnam: [['RK Beach','Seafront promenade'],['Kailasagiri','Hilltop park and views'],['Submarine Museum','Maritime museum'],['Araku Valley','Mountain and tribal culture'],['Borra Caves','Limestone cave system'],['Simhachalam Temple','Hilltop temple'],['Yarada Beach','Scenic coastal beach'],['Dolphin’s Nose','Coastal viewpoint']]
  };
  Object.entries(expandedPlaces).forEach(([city, places]) => { famousPlaces[city] = places.map(([name,desc], i) => [name, desc, placeFallback[i % placeFallback.length][2]]); });
  let placesRenderToken = 0;
  async function updateFamousPlaces(city) {
    const box = document.getElementById('placesBox'), grid = document.getElementById('placesGrid');
    if (!box || !grid || !city) return;
    const token = ++placesRenderToken;
    const selectedCity = String(city).trim();
    const mappedCity = Object.keys(famousPlaces).find(key => key.toLowerCase() === selectedCity.toLowerCase());
    const items = mappedCity ? famousPlaces[mappedCity] : placeFallback.map(([name,desc,img]) => [`${selectedCity} ${name}`, `${desc} around ${selectedCity}`, img]);
    document.getElementById('placesTitle').textContent = `Best places to visit in ${selectedCity}`;
    document.getElementById('placesSubtitle').textContent = `Famous attractions and local experiences around ${selectedCity}.`;
    grid.innerHTML = items.map(([name,desc,img]) => `<article class="place-card live-place-card" data-place-name="${esc(name)}"><div class="place-image" style="background-image:url('${img}')"><span>📍</span></div><div class="place-body"><h3>${esc(name)}</h3><p>${esc(desc)}</p></div></article>`).join('');
    box.hidden = false;
    const photos = await Promise.all(items.map(async ([name,,fallback]) => { try { const response=await fetch(`https://en.wikipedia.org/api/rest_v1/page/summary/${encodeURIComponent(name.replace(/[’']/g,''))}`); const data=await response.json(); return data?.originalimage?.source || data?.thumbnail?.source || fallback; } catch (_) { return fallback; } }));
    if (token !== placesRenderToken) return;
    grid.querySelectorAll('.live-place-card').forEach((card, i) => { const image=card.querySelector('.place-image'); if (image && photos[i]) image.style.backgroundImage=`url("${photos[i]}")`; card.title=`Open ${card.dataset.placeName} on Wikipedia`; card.addEventListener('click',()=>window.open(`https://en.wikipedia.org/wiki/${encodeURIComponent(card.dataset.placeName.replace(/ /g,'_'))}`,'_blank','noopener')); });
  }
  function wirePlaceSelection() {
    const city = document.getElementById('city');
    const destination = document.getElementById('destination');
    const refresh = () => setTimeout(() => updateFamousPlaces(city?.value || destination?.value || ''), 50);
    city?.addEventListener('change', refresh); destination?.addEventListener('change', refresh);
    refresh();
  }
  function refreshLiveHotelDisplay() {
    if (!allHotels.length || !document.getElementById('hotelGrid')?.children.length) return;
    renderHotels();
    if (document.getElementById('hotelCompareModal')?.classList.contains('open') && selectedHotels.length === 2) renderCompare();
  }
  function wireCurrencyAndLanguage() {
    document.getElementById('currencySelect')?.addEventListener('change', refreshLiveHotelDisplay);
    document.getElementById('languageSelect')?.addEventListener('change', refreshLiveHotelDisplay);
    // Keep the live cards aligned with the page’s existing exchange-rate refresh.
    fetch('https://open.er-api.com/v6/latest/INR', { cache: 'no-store' }).then(r => r.json()).then(data => {
      if (data?.result === 'success' && data.rates) { Object.keys(currencyRates).forEach(code => { if (Number.isFinite(data.rates[code])) currencyRates[code] = data.rates[code]; }); refreshLiveHotelDisplay(); }
    }).catch(() => {});
  }
  function openHotelDetails(hotel) {
    if (!hotel) return;
    window.gontobboAddRecent?.(hotel);
    let modal = document.getElementById('liveHotelDetailsModal');
    if (!modal) { modal = document.createElement('div'); modal.id='liveHotelDetailsModal'; modal.className='live-details-modal'; modal.setAttribute('aria-hidden','true'); document.body.appendChild(modal); modal.addEventListener('click',e=>{if(e.target===modal||e.target.closest('.live-details-close')){modal.classList.remove('open');modal.setAttribute('aria-hidden','true');document.body.style.overflow='';}}); }
    const providerImages=Array.isArray(hotel.images)?hotel.images:[];
    const images=[...new Set([hotel.img,...providerImages])].filter(Boolean).slice(0,8);
    const officialHotelSites = {
      'Alila Diwa Goa Getaway':'https://www.alilahotels.com/diwa-goa/',
      'Rambagh Palace, Jaipur':'https://www.tajhotels.com/en-in/hotels/rambagh-palace-jaipur',
      'The Oberoi Grand, Kolkata':'https://www.oberoihotels.com/kolkata/',
      'Taj Lands End, Mumbai':'https://www.tajhotels.com/en-in/hotels/taj-lands-end-mumbai'
    };
    const bookingUrl=officialHotelSites[hotel.name] || hotel.booking_url || '';
    const mapQuery = hotel.latitude && hotel.longitude ? `${hotel.latitude},${hotel.longitude}` : `${hotel.name}, ${hotel.city||''}, ${hotel.state||''}`;
    const mapUrl = `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(mapQuery)}`;
    const bookingButton=bookingUrl?`<a class="live-details-book" href="${esc(bookingUrl)}" target="_blank" rel="noopener">▣ Book on hotel website ↗</a>`:'';
    const phoneDigits=String(hotel.phone||'').replace(/[^\d+]/g,'');
    const contactQuery = `${hotel.name || ''}, ${hotel.city || ''}, ${hotel.state || ''}`.replace(/,\s*,/g, ',').trim();
    const phoneButton=phoneDigits?`<a class="live-details-call" href="tel:${esc(phoneDigits)}">☎ Call to book ${esc(hotel.phone)}</a>`:`<span class="live-details-contact-loading" data-contact-slot>Finding hotel contact…</span>`;
    modal.innerHTML=`<div class="live-details-panel" role="dialog" aria-modal="true" aria-labelledby="liveDetailsTitle"><button type="button" class="live-details-close" aria-label="Close hotel details">×</button><div class="live-details-gallery"><img class="live-details-hero" src="${esc(images[0])}" alt="${esc(hotel.name)}"><div class="live-details-thumbs">${images.slice(1).map((img,i)=>`<img src="${esc(img)}" alt="${esc(hotel.name)} photo ${i+2}" loading="lazy">`).join('')}</div></div><div class="live-details-content"><p class="live-details-kicker">${esc(hotel.type||'Hotel')} · ${esc(hotel.city||'')}</p><h2 id="liveDetailsTitle">${esc(hotel.name)}</h2><div class="live-details-price"><strong>${money(hotel.price)}</strong> <span>${esc(label('night'))}</span></div><p class="live-details-rating">★ ${esc(hotel.rating||'—')} · ${esc(hotel.stars||'—')} ${esc(label('stars'))} · ${esc(hotel.reviews||0)} reviews</p><div class="live-details-amenities">${(hotel.facilities||['Wi-Fi','Air conditioning','Breakfast available']).slice(0,6).map(x=>`<span>✓ ${esc(x)}</span>`).join('')}</div><div class="live-details-buttons">${bookingButton}${phoneButton}<a class="live-details-map" href="${esc(mapUrl)}" target="_blank" rel="noopener">📍 View hotel on map</a><button type="button" class="live-details-save">${window.gontobboIsFavorite?.(hotel.id)?'♥ Saved to favorites':'♡ Save to favorites'}</button></div></div></div>`;
    const hero=modal.querySelector('.live-details-hero'); modal.querySelectorAll('.live-details-thumbs img').forEach(img=>img.addEventListener('click',()=>{hero.src=img.src;})); modal.querySelector('.live-details-save')?.addEventListener('click',()=>{window.gontobboToggleFavorite?.(hotel.id,hotel);modal.querySelector('.live-details-save').textContent=window.gontobboIsFavorite?.(hotel.id)?'♥ Saved to favorites':'♡ Save to favorites';}); modal.classList.add('open'); modal.setAttribute('aria-hidden','false'); document.body.style.overflow='hidden';
    if (!hotel.phone) { const contactParam=hotel.property_token?`property_token=${encodeURIComponent(hotel.property_token)}`:`query=${encodeURIComponent(contactQuery)}`; fetch(`/api/travel/hotels/contact?${contactParam}`).then(r=>r.json()).then(data=>{ const slot=modal.querySelector('[data-contact-slot]'); if (!slot) return; if (data.phone) { hotel.phone=data.phone; const digits=String(data.phone).replace(/[^\d+]/g,''); slot.outerHTML=`<a class="live-details-call" href="tel:${esc(digits)}">☎ Call to book ${esc(data.phone)}</a>`; } else slot.textContent='Phone number not listed by provider'; }).catch(()=>{ const slot=modal.querySelector('[data-contact-slot]'); if (slot) slot.textContent='Phone number not listed by provider'; }); }
  }

  const trainRoutes = {
    'Kolkata|Delhi': [['Rajdhani Express','12301','17h 05m','₹2,450','AC 2 Tier'],['Poorva Express','12303','18h 10m','₹2,180','AC 2 Tier']],
    'Mumbai|Goa': [['Konkan Kanya Express','10111','11h 40m','₹1,120','AC 2 Tier'],['Jan Shatabdi Express','12051','8h 35m','₹850','AC Chair Car']],
    'Chennai|Bengaluru': [['Shatabdi Express','12027','4h 25m','₹1,450','AC Chair Car'],['Brindavan Express','12639','5h 10m','₹780','Chair Car']],
    'Delhi|Jaipur': [['Ajmer Shatabdi','12015','4h 35m','₹1,100','AC Chair Car'],['Vande Bharat Express','20977','4h 15m','₹1,250','AC Chair Car']]
  };
  const airlineOfficialSites = {
    'indigo': 'https://www.goindigo.in/', 'air india': 'https://www.airindia.com/', 'vistara': 'https://www.airvistara.com/',
    'spicejet': 'https://www.spicejet.com/', 'akasa air': 'https://www.akasaair.com/', 'go first': 'https://www.flygofirst.com/',
    'emirates': 'https://www.emirates.com/', 'qatar airways': 'https://www.qatarairways.com/', 'etihad': 'https://www.etihad.com/',
    'singapore airlines': 'https://www.singaporeair.com/', 'lufthansa': 'https://www.lufthansa.com/', 'british airways': 'https://www.britishairways.com/',
    'thai airways': 'https://www.thaiairways.com/', 'malaysia airlines': 'https://www.malaysiaairlines.com/', 'air asia': 'https://www.airasia.com/'
  };
  function officialAirlineUrl(airline) {
    const name=String(airline||'').toLowerCase();
    const key=Object.keys(airlineOfficialSites).find(k=>name.includes(k));
    return key ? airlineOfficialSites[key] : `https://www.google.com/search?q=${encodeURIComponent(String(airline||'airline')+' official website booking')}`;
  }
  function renderTrainResults(from, to, date, results) {
    const routes = trainRoutes[`${from}|${to}`] || trainRoutes[`${to}|${from}`] || [['Intercity Express','12001','6h 30m','₹950','AC Chair Car'],['Superfast Express','12901','8h 15m','₹1,280','AC 3 Tier']];
    results.hidden = false;
    results.innerHTML = `<div class="travel-results-heading"><b>Train options</b><span>${esc(from)} → ${esc(to)} · ${esc(date)}</span></div>` + routes.map(r => `<article class="route-card travel-option-card"><div class="travel-option-main"><div><strong>🚆 ${esc(r[0])}</strong><small>Train ${esc(r[1])} · ${esc(r[4])}</small></div><strong>${esc(r[3])}</strong></div><p>${esc(from)} → ${esc(to)} · ${esc(r[2])}</p><a class="official-book-btn" href="https://www.irctc.co.in/nget/train-search" target="_blank" rel="noopener">Book on official IRCTC site ↗</a></article>`).join('');
  }

  async function searchHotels(event) {
    event.preventDefault(); event.stopImmediatePropagation();
    const state = document.getElementById('destination')?.value, city = document.getElementById('city')?.value;
    const checkIn = document.getElementById('homeCheckIn')?.value, checkOut = document.getElementById('homeCheckOut')?.value;
    const grid = document.getElementById('hotelGrid');
    if (!state || !city || !checkIn || !checkOut) return;
    const guestText = document.getElementById('homeGuestBtn')?.textContent || '';
    const adults = Math.max(1, Number((guestText.match(/(\d+)\s*Adult/) || [])[1] || 2));
    const children = Number((guestText.match(/(\d+)\s*Children/) || [])[1] || 0), rooms = Number((guestText.match(/(\d+)\s*Room/) || [])[1] || 1);
    grid.innerHTML = '<div style="padding:20px">Searching live hotel availability…</div>'; document.getElementById('hotelResults')?.classList.add('show');
    try {
      const res = await api('/api/travel/hotels', { method: 'POST', body: JSON.stringify({ city, state, check_in_date: checkIn, check_out_date: checkOut, adults, children, rooms, currency: 'INR' }) });
      const data = await res.json(); if (!res.ok) throw new Error(data?.error?.message || data?.message || 'Hotel search failed');
      allHotels = (data.hotels?.options || []).filter(h => Number(h.price) > 0); selectedHotels = []; wireHotelControls(); renderHotels();
      const summary = document.getElementById('resultsSummary'); if (summary) summary.textContent = `${allHotels.length} live stays found in ${city}, ${state}`;
    } catch (error) { showStatus(grid, error.message, true); }
  }
  async function searchFlights(event) {
    event.preventDefault(); event.stopImmediatePropagation();
    const from = document.getElementById('transportFromState')?.value, to = document.getElementById('transportToState')?.value, departure = document.getElementById('transportDate')?.value, results = document.getElementById('transportResults');
    if (!from || !to || !departure) return; results.hidden = false; results.innerHTML = '<div style="padding:18px">Searching live flights…</div>';
    const mode = document.querySelector('.transport-tab.active')?.dataset.mode || 'flight';
    if (mode === 'train') { renderTrainResults(from, to, departure, results); return; }
    const adults = Math.max(1, Number(document.getElementById('transportAdultsCount')?.textContent || 1)), children = Math.max(0, Number(document.getElementById('transportChildrenCount')?.textContent || 0));
    try { const res = await api('/api/travel/flights', { method: 'POST', body: JSON.stringify({ from_location: from, to_location: to, departure_date: departure, adults, children, currency: 'INR' }) }); const data = await res.json(); if (!res.ok) throw new Error(data?.error?.message || data?.message || 'Flight search failed'); const flights = data.flights?.options || []; if (!flights.length) return showStatus(results, 'No live flights were found for this route and date.'); results.innerHTML = flights.map(f => `<article class="route-card" style="padding:18px;margin:10px 0"><div style="display:flex;justify-content:space-between;gap:16px;flex-wrap:wrap"><div><strong>${esc(f.airline)}</strong> · ${esc(f.flight_number)}</div><strong>${money(f.price, f.currency)}</strong></div><p>${esc(f.departure?.airport)} ${esc(f.departure?.time)} → ${esc(f.arrival?.airport)} ${esc(f.arrival?.time)}</p><small>${esc(f.duration_text)} · ${esc(f.stops_text)} · ${esc(f.travel_class)}</small><br><a class="official-book-btn" href="${esc(officialAirlineUrl(f.airline))}" target="_blank" rel="noopener">Book on official ${esc(f.airline)} site ↗</a></article>`).join(''); } catch (error) { showStatus(results, error.message, true); }
  }
  const style = document.createElement('style'); style.textContent = `.live-compare-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px}.deal-grid,.rated-grid,.discover-grid{display:flex!important;flex-wrap:nowrap!important;overflow-x:auto!important;overflow-y:hidden!important;scroll-behavior:smooth!important;scroll-snap-type:x proximity!important;padding:4px 4px 16px!important;cursor:grab}.deal-grid:active,.rated-grid:active,.discover-grid:active{cursor:grabbing}.deal-grid>.deal-card,.rated-grid>.rated-card,.discover-grid>.discover-card{flex:0 0 min(330px,82vw)!important;scroll-snap-align:start!important}.deal-grid::-webkit-scrollbar,.rated-grid::-webkit-scrollbar,.discover-grid::-webkit-scrollbar{height:9px}.deal-grid::-webkit-scrollbar-thumb,.rated-grid::-webkit-scrollbar-thumb,.discover-grid::-webkit-scrollbar-thumb{background:#b6a9e8;border-radius:9px}.live-place-card{overflow:hidden!important}.live-place-card .place-image{height:150px!important;background-size:cover!important;background-position:center!important;display:flex;align-items:flex-start;justify-content:flex-end;padding:12px}.live-place-card .place-image span{background:#fff;border-radius:50%;padding:6px}.live-hotel-actions{display:flex;gap:8px;margin-top:14px}.live-hotel-actions button{padding:9px 12px;border-radius:10px;font-size:12px}.live-favorite-btn{background:#fff!important;color:#5a469f!important;border:1px solid #d8cff5!important}.live-view-btn{background:#6954c6!important;color:#fff!important}.travel-results-heading{display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap;padding:12px 4px;color:#554a79}.travel-option-card{padding:18px!important;margin:10px 0!important}.travel-option-main{display:flex;justify-content:space-between;gap:16px;flex-wrap:wrap}.travel-option-main small{display:block;color:#746a93;margin-top:6px}.travel-select-btn{padding:9px 14px;border-radius:10px}@media(max-width:650px){.live-compare-grid{grid-template-columns:1fr}.live-hotel-actions button{flex:1}}`; document.head.appendChild(style);
  const detailStyle = document.createElement('style'); detailStyle.textContent = `.live-details-modal{position:fixed;inset:0;z-index:9999;background:rgba(25,18,51,.68);display:none;align-items:center;justify-content:center;padding:20px}.live-details-modal.open{display:flex}.live-details-panel{position:relative;width:min(760px,100%);max-height:92vh;overflow:auto;background:#fff;border-radius:24px;box-shadow:0 22px 70px rgba(20,10,55,.35)}.live-details-close{position:absolute;right:16px;top:14px;z-index:2;border:0;background:#fff;border-radius:50%;width:38px;height:38px;font-size:25px;cursor:pointer}.live-details-gallery{padding:14px 14px 0}.live-details-hero{width:100%;height:330px;object-fit:cover;border-radius:16px}.live-details-thumbs{display:flex;gap:10px;margin-top:10px;overflow-x:auto}.live-details-thumbs img{width:92px;height:68px;object-fit:cover;border-radius:10px;cursor:pointer}.live-details-content{padding:20px 24px 26px}.live-details-kicker{color:#766a9d;text-transform:uppercase;font-size:11px;letter-spacing:1px}.live-details-content h2{margin:6px 0 10px;color:#271d54}.live-details-price strong{font-size:24px;color:#5d46bc}.live-details-price span,.live-details-rating{color:#756b91}.live-details-amenities{display:flex;flex-wrap:wrap;gap:8px;margin:18px 0}.live-details-amenities span{background:#f3f0ff;border-radius:20px;padding:8px 11px;font-size:12px;color:#4b3c86}.live-details-buttons{display:flex;gap:10px;flex-wrap:wrap}.live-details-map,.live-details-save,.live-details-book,.live-details-call{border:0;border-radius:10px;padding:11px 16px;cursor:pointer;text-decoration:none;font-size:13px}.live-details-map{background:#f0edff;color:#513c9f}.live-details-save{background:#6954c6;color:#fff}.live-details-book{background:#3b2b83;color:#fff!important}.live-details-call{background:#e7f7ef;color:#167348!important}.live-details-contact-loading{padding:11px 16px;border-radius:10px;background:#f6f3ff;color:#756b91;font-size:13px}.official-book-btn{display:inline-block;margin-top:12px;padding:10px 14px;border-radius:10px;background:#6954c6;color:#fff!important;text-decoration:none;font-size:13px}@media(max-width:650px){.live-details-modal{padding:10px}.live-details-panel{border-radius:18px}.live-details-hero{height:230px}.live-details-content{padding:16px}}
  `; document.head.appendChild(detailStyle);
  wirePlaceSelection();
  wireCurrencyAndLanguage();
  document.getElementById('searchHotelsBtn')?.addEventListener('click', searchHotels, true);
  document.getElementById('transportForm')?.addEventListener('submit', searchFlights, true);
  document.addEventListener('click', e => {
    const button = e.target.closest?.('.deal-btn, .rated-btn');
    if (!button) return;
    e.preventDefault(); e.stopImmediatePropagation();
    exploreFeaturedHotel(button);
  }, true);
  const discoverWikipedia = {
    'mumbai': 'https://en.wikipedia.org/wiki/Mumbai',
    'goa': 'https://en.wikipedia.org/wiki/Goa',
    'jaipur': 'https://en.wikipedia.org/wiki/Jaipur'
  };
  document.addEventListener('click', e => {
    const card = e.target.closest?.('.discover-card');
    if (!card) return;
    if (card.dataset.wikipedia) { e.preventDefault(); window.location.href = card.dataset.wikipedia; return; }
    const heading = card.querySelector('h3')?.textContent || '';
    const city = Object.keys(discoverWikipedia).find(key => heading.toLowerCase().includes(key));
    if (!city) return;
    e.preventDefault();
    window.location.assign(discoverWikipedia[city]);
  });
  document.querySelectorAll('.discover-card').forEach(card => { card.setAttribute('role','link'); card.setAttribute('tabindex','0'); card.style.cursor='pointer'; });
})();
