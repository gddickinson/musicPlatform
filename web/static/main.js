// Entry point: registers the lazily loaded pages, sets the footer mode text, draws the background and starts the router.
import { start, route, lazy, app, isStatic, $ } from './core.js';
import { drawBackground } from './background.js';

const PAGES = { 'home.js': ['home'], 'drums.js': ['drums'], 'synth.js': ['synth'], 'piano.js': ['piano'],
  'verify.js': ['verify'], 'about.js': ['about'] };
lazy(Object.fromEntries(Object.entries(PAGES).flatMap(([file, names]) => names.map(n => [n, () => import('./' + file)]))));

route('notfound', () => { app().innerHTML = '<h1>Not found</h1><p><a href="#/">Back to the start</a></p>'; });

$('#mode').textContent = isStatic() ? 'static site: the instruments run in your browser'
  : 'local app (Python server): the instruments run in your browser, and can be re-checked against the Python';
drawBackground($('#bg'));
start();
