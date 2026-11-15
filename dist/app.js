const $ = id => document.getElementById(id);
const svg = (tag, attrs = {}) => {
  const node = document.createElementNS('http://www.w3.org/2000/svg', tag);
  for (const [key, value] of Object.entries(attrs)) node.setAttribute(key, value);
  return node;
};

const earthSearch = 'https://earth-search.aws.element84.com/v1/collections/sentinel-2-l2a';
const gcovGuide = 'https://nisar-docs.asf.alaska.edu/gcov/';
const boundaries = new Map();
const mapLabels = [
  { name: 'KAZAKHSTAN', lon: 75.4, lat: 44.10 },
  { name: 'KYRGYZSTAN', lon: 74.15, lat: 41.30 },
  { name: 'UZBEKISTAN', lon: 69.8, lat: 41.55 },
  { name: 'TAJIKISTAN', lon: 70.25, lat: 39.15 },
  { name: 'CHINA', lon: 79.6, lat: 40.50 }
];
let lakes = [];
let borders;
let lake;
let series;
let mapScale = 'region';
let mapRender = 0;
let dateA;
let dateB;

async function requestJson(path) {
  const response = await fetch(path);
  if (!response.ok) throw new Error(`Could not load ${path}`);
  return response.json();
}

function formattedDate(timestamp) {
  return new Intl.DateTimeFormat('en-GB', {
    day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC',
  }).format(new Date(timestamp));
}

function polygonPath(geometry, project) {
  if (!geometry) return '';
  if (geometry.type === 'GeometryCollection') return geometry.geometries.map(g => polygonPath(g, project)).join(' ');
  if (!['Polygon', 'MultiPolygon'].includes(geometry.type)) return '';
  const polygons = geometry.type === 'Polygon' ? [geometry.coordinates] : geometry.coordinates;
  return polygons.flatMap(polygon => polygon.map(ring => {
    const points = ring.map(([lon, lat]) => project(lon, lat).map(value => value.toFixed(2)).join(','));
    return points.length ? `M ${points.join(' L ')} Z` : '';
  })).join(' ');
}

function viewProject(west, south, east, north) {
  const ratio = Math.cos((south + north) / 2 * Math.PI / 180);
  const s = Math.min(488 / ((east - west) * ratio), 308 / (north - south));
  return (lon, lat) => [260 + (lon - (east + west) / 2) * ratio * s, 170 - (lat - (south + north) / 2) * s];
}

function label(parent, text, x, y, attributes = {}) {
  const element = svg('text', {x, y, class: 'map-label', ...attributes});
  element.textContent = text;
  parent.append(element);
}

function renderRegion() {
  const canvas = $('map');
  const project = viewProject(68.0, 38.8, 81.3, 44.5);
  for (let lon = 68; lon <= 82; lon += 2) {
    const [x] = project(lon, 42);
    canvas.append(svg('line', {x1:x, x2:x, y1:0, y2:340, class:'map-grid'}));
  }
  for (let lat = 39; lat <= 45; lat++) {
    const [,y] = project(75, lat);
    canvas.append(svg('line', {x1:0, x2:520, y1:y, y2:y, class:'map-grid'}));
  }
  for (const feature of borders.features) {
    const code = feature.properties.code.toLowerCase();
    canvas.append(svg('path', {d: polygonPath(feature.geometry, project), class: `country ${code}`, 'fill-rule':'evenodd'}));
  }
  for (const place of mapLabels) label(canvas, place.name, ...project(place.lon, place.lat), {'text-anchor':'middle'});

  const positioned = [];
  for (const item of lakes) {
    const [x,y] = project(item.lon, item.lat);
    const near = positioned.find(([oldX,oldY]) => Math.hypot(x-oldX,y-oldY) < 19);
    const shownX = near ? x + 13 : x;
    const shownY = near ? y + 15 : y;
    positioned.push([x,y]);
    const marker = svg('g', {class:'map-marker', role:'button', tabindex:'0', 'aria-label':item.name, 'aria-pressed':String(item.id === lake.id)});
    if (near) marker.append(svg('line', {x1:x, y1:y, x2:shownX, y2:shownY}));
    marker.append(svg('circle', {cx:shownX,cy:shownY,r:8}));
    const title = svg('title');
    title.textContent = item.name;
    marker.append(title);
    marker.addEventListener('click', () => chooseLake(item.id));
    marker.addEventListener('keydown', event => {
      if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        chooseLake(item.id);
      }
    });
    canvas.append(marker);
  }
  label(canvas, '↑ N', 494, 24);
  $('map-caption').textContent = 'Natural Earth · WGS84';
}

async function renderMap() {
  const thisRender = ++mapRender;
  const canvas = $('map');
  canvas.replaceChildren();
  $('region-button').setAttribute('aria-pressed', String(mapScale === 'region'));
  $('local-button').setAttribute('aria-pressed', String(mapScale === 'lake'));
  if (mapScale === 'region') {
    renderRegion();
    return;
  }
  const [a, b] = pair();
  canvas.setAttribute('aria-label', `${lake.name} study area`);
  const ring = lake.extent.coordinates[0];
  const xs = ring.map(point => point[0]);
  const ys = ring.map(point => point[1]);
  const project = viewProject(Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys));
  canvas.append(svg('path', {d:polygonPath(lake.extent, project), fill:'#1c3436', stroke:'#637b78', 'stroke-dasharray':'5 4'}));
  label(canvas, 'STUDY AREA', 19, 22);
  label(canvas, '↑ N', 494, 24);
  $('map-caption').textContent = 'A cyan · B amber · WGS84';
  try {
    const outlines = await Promise.all([a,b].map(obs => {
      const path = obs.files.boundary;
      if (!boundaries.has(path)) boundaries.set(path, requestJson(path).catch(error => {
        boundaries.delete(path);
        throw error;
      }));
      return boundaries.get(path);
    }));
    if (thisRender !== mapRender) return;
    [1, 0].forEach(i => {
      for (const feature of outlines[i].features) {
        canvas.append(svg('path', {d:polygonPath(feature.geometry, project), class:i ? 'map-water secondary' : 'map-water', 'fill-rule':'evenodd'}));
      }
    });
  } catch {
    if (thisRender === mapRender) $('map-caption').textContent = 'Outline geometry could not load';
  }
}

function options(select, observations, value) {
  select.replaceChildren(...observations.map(obs => new Option(formattedDate(obs.datetime), obs.id)));
  select.value = value;
}

function pair() {
  return [dateA,dateB].map(id => series.observations.find(obs => obs.id === id));
}

function seriesLabel(entry) {
  return entry.key === 'radar' ? 'NISAR radar' : 'Sentinel-2 optical';
}

function chooseLake(id) {
  lake = lakes.find(entry => entry.id === id);
  $('lake-title').textContent = lake.name;
  $('lake-region').textContent = lake.region;
  $('lake-context').textContent = lake.context;
  $('lake-reference').href = lake.reference;
  for (const button of $('lake-list').querySelectorAll('button')) {
    button.setAttribute('aria-pressed', String(button.dataset.lake === id));
  }
  $('series').replaceChildren(...lake.series.map(entry => {
    const button = document.createElement('button');
    button.type = 'button';
    button.textContent = seriesLabel(entry);
    button.dataset.series = entry.key;
    button.addEventListener('click', () => chooseSeries(entry));
    return button;
  }));
  chooseSeries(lake.series[0]);
}

function chooseSeries(entry) {
  series = entry;
  [dateA, dateB] = entry.defaultDates;
  for (const button of $('series').querySelectorAll('button')) {
    button.setAttribute('aria-pressed', String(button.dataset.series === entry.key));
  }
  $('wipe').value = 50;
  updateWipe();
  renderComparison();
}

function formatArea(value, signed = false, precision = 2) {
  return new Intl.NumberFormat('en', {
    maximumFractionDigits: precision, minimumFractionDigits: precision,
    signDisplay: signed ? 'exceptZero' : 'auto',
  }).format(Math.abs(value) < .5 * 10 ** -precision ? 0 : value);
}

function metric(id, value, unit) {
  const span = document.createElement('small');
  span.textContent = unit;
  $(id).replaceChildren(document.createTextNode(`${value} `), span);
}

function updateWipe() {
  $('scene').style.setProperty('--compare', `${$('wipe').value}%`);
}

function sourceBox(observation, tag, precision) {
  const q = observation.quality;
  const box = document.createElement('details');
  const summary = document.createElement('summary');
  summary.textContent = `${tag} · ${formattedDate(observation.datetime)} · ${observation.satellite}`;
  const rows = [
    ['Acquisition (UTC)', observation.datetime],
    ['Provider', observation.provider],
    ['Product', observation.product],
    ['Collection', observation.collection],
    ['Granule', observation.granule],
    ['Processing', observation.release ? `${observation.maturity} · ${observation.release} · track ${observation.track} ${observation.direction.toLowerCase()}` : `Baseline ${observation.baseline}`],
    ['Method', observation.method],
    ['Quality', `${q.status} · ${(q.validFraction * 100).toFixed(1)}% eligible over the lake and shoreline check. ${q.review || ''}`],
    ['Sensitivity range', `${formatArea(q.lowKm2, false, precision)}–${formatArea(q.highKm2, false, precision)} km²; includes threshold variation and excluded pixels.`],
    ['Unobserved area', `${formatArea(q.unknownKm2, false, precision)} km² in the quality-check footprint`],
  ];
  if (q.opticalComparison) rows.push(['Optical overlap', `${Math.round(q.opticalComparison.iou * 100)}% intersection over union on shared clear pixels. Reference ${formattedDate(q.opticalComparison.datetime)} · ${q.opticalComparison.scene}.`]);
  const definition = document.createElement('dl');
  definition.className = 'source-data';
  for (const [title, value] of rows) {
    const dt = document.createElement('dt');
    const dd = document.createElement('dd');
    dt.textContent = title;
    dd.textContent = value;
    definition.append(dt,dd);
  }
  const links = document.createElement('div');
  links.className = 'source-links';
  for (const [text, href] of [
    ['Original source ↗', observation.source], ['Water boundary (GeoJSON)', observation.files.boundary],
    ['Pixel mask (GeoTIFF)', observation.files.mask]
  ]) {
    const link = document.createElement('a');
    link.textContent = text;
    link.href = href;
    link.target = '_blank';
    link.rel = 'noopener';
    links.append(link);
  }
  box.append(summary, definition, links);
  return box;
}

function renderComparison() {
  const list = series.observations;
  const aIndex = list.findIndex(obs => obs.id === dateA);
  if (list.findIndex(obs => obs.id === dateB) <= aIndex) dateB = list.at(-1).id;
  options($('date-a'), list.slice(0, -1), dateA);
  options($('date-b'), list.slice(aIndex + 1), dateB);
  const [a,b] = pair();
  for (const [key, obs] of [['a', a], ['b', b]]) {
    $(`image-${key}`).src = obs.files.image;
    $(`image-${key}`).alt = `${lake.name} on ${formattedDate(obs.datetime)}, ${obs.satellite}`;
    $(`overlay-${key}`).src = obs.files.overlay;
    $(`stamp-${key}`).textContent = `${key.toUpperCase()} · ${formattedDate(obs.datetime)}`;
  }
  const delta = b.areaKm2 - a.areaKm2;
  const digits = Math.max(a.areaKm2, b.areaKm2) < .1 ? 3 : 2;
  metric('area-a', formatArea(a.areaKm2, false, digits), 'km²');
  metric('area-b', formatArea(b.areaKm2, false, digits), 'km²');
  metric('area-change', formatArea(delta, true, digits), 'km²');
  metric('relative-change', a.areaKm2 ? formatArea(100 * delta / a.areaKm2, true, 1) : '—', a.areaKm2 ? '%' : '');
  const interval = Math.round((Date.parse(b.datetime) - Date.parse(a.datetime)) / 86_400_000);
  const overlap = a.quality.lowKm2 <= b.quality.highKm2 && b.quality.lowKm2 <= a.quality.highKm2;
  const coverageLimited = Math.min(a.quality.validFraction, b.quality.validFraction) < .95;
  const seasonA = Date.parse(`2000-${a.datetime.slice(5,10)}`);
  const seasonB = Date.parse(`2000-${b.datetime.slice(5,10)}`);
  const seasonal = Math.abs(seasonB - seasonA) / 86_400_000 > 21;
  $('quality').textContent = `${interval} days between scenes. ${overlap
    ? 'The sensitivity ranges overlap. The measured difference is unresolved.'
    : 'The estimates are separated under the tested thresholds. Conditions at the shoreline can still influence the difference.'}${coverageLimited ? ' Some shoreline pixels were excluded. See coverage and sensitivity for each date.' : ''}${seasonal ? ' Acquisition dates are more than three weeks apart within the summer season.' : ''}`;
  $('scale-text').textContent = `${a.grid.pixelMetres} m analysis grid`;
  const method = $('method-description');
  const link = document.createElement('a');
  link.href = series.key === 'radar' ? gcovGuide : earthSearch;
  link.textContent = series.key === 'radar' ? 'ASF GCOV documentation ↗' : 'Earth Search collection ↗';
  link.target = '_blank';
  link.rel = 'noopener';
  method.replaceChildren(document.createTextNode(series.key === 'radar'
    ? 'Frequency A HH backscatter from two same-track NISAR scenes. Invalid subswaths and low-look pixels are excluded. Radar shadow, rough water and ice can alter the signal. '
    : 'Sentinel-2 reflectance indices identify connected water within each lake basin. Scene classification excludes cloud, shadow, snow, unclassified and missing pixels. The 20 m SWIR band is resampled onto the 10 m grid. '), link);
  $('sources').replaceChildren(sourceBox(a, 'Observation A', digits), sourceBox(b, 'Observation B', digits));
  $('map').setAttribute('aria-label', 'Interactive map of Kyrgyzstan');
  renderMap();
}

$('date-a').addEventListener('change', event => { dateA = event.target.value; renderComparison(); });
$('date-b').addEventListener('change', event => { dateB = event.target.value; renderComparison(); });
$('wipe').addEventListener('input', updateWipe);
$('outline-toggle').addEventListener('change', event => {
  document.querySelectorAll('.outline').forEach(node => { node.hidden = !event.target.checked; });
});
$('region-button').addEventListener('click', () => { mapScale = 'region'; renderMap(); });
$('local-button').addEventListener('click', () => { mapScale = 'lake'; renderMap(); });
for (const id of ['image-a','image-b','overlay-a','overlay-b']) {
  $(id).addEventListener('error', () => { $('quality').textContent = 'An observation image failed to load. Refresh to retry.'; });
}

try {
  const [inventory, geography] = await Promise.all([requestJson('data/inventory.json'), requestJson('data/region.geojson')]);
  lakes = inventory.lakes;
  borders = geography;
  if (!lakes.length) throw new Error('No reviewed observation pairs');
  for (const entry of lakes) {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'lake-option';
    button.dataset.lake = entry.id;
    const dot = document.createElement('i');
    const description = document.createElement('span');
    const title = document.createElement('strong');
    const region = document.createElement('small');
    const arrow = document.createElement('span');
    title.textContent = entry.name;
    region.textContent = entry.region;
    arrow.className = 'arrow';
    arrow.textContent = '→';
    arrow.setAttribute('aria-hidden', 'true');
    description.append(title,region);
    button.append(dot,description,arrow);
    button.addEventListener('click', () => chooseLake(entry.id));
    $('lake-list').append(button);
  }
  chooseLake(lakes[0].id);
  for (const id of ['explorer','method']) $(id).hidden = false;
  $('loading').hidden = true;
} catch (error) {
  $('loading').textContent = `The observation inventory is unavailable. ${error.message}.`;
}
