/* wizard_dom_shim.js -- the smallest DOM that can render wizard/wizard.html, and the ONLY
   property of a real one that matters here: A NODE IS NOT IN THE DOCUMENT UNTIL SOMETHING
   ATTACHES IT.

   That is the bug this exists to catch. `renderSeedSizeTab()` built its containers, called
   `paintSeedSize()` -- which finds them with `document.querySelector` -- and returned the tree to
   a caller who appended it afterwards. The lookup ran against a detached tree, got null, and took
   the "not the tab on screen" early return, so the Seed size step drew NOTHING on arrival:
   no size figures, no composition bars, no contribution card, until the player touched a control
   and an event handler called refresh(). Introduced 2026-08-08 in 9566a4d, by the refactor that
   made repaint possible; nothing was red for three days, because a page that renders an empty div
   throws no error.

   So `querySelector` here resolves an id ONLY if that node's parent chain reaches a node that was
   in the static HTML. Everything else in this file is scaffolding. It is deliberately NOT jsdom:
   npm is not reachable from CI's offline steps, and a full DOM would model a hundred behaviours
   this page does not use while making the one that matters invisible. */

const NODES = [];

class El {
  constructor(tag){
    this.tagName = String(tag || "div").toUpperCase();
    this.id = ""; this.className = ""; this._html = ""; this._text = "";
    this.kids = []; this.parent = null; this.style = {}; this.listeners = {};
    this._static = false;
    NODES.push(this);
  }
  set innerHTML(h){ this._html = String(h); this.kids = []; this._adopt(h); }  // children go
  get innerHTML(){ return this._html; }
  set textContent(t){ this._text = String(t); this.kids = []; this._html = ""; }
  get textContent(){ return this._text || stripTags(this._html); }
  insertAdjacentHTML(_pos, h){ this._html += String(h); this._adopt(h); }
  /* Markup assigned as a string still produces REAL, FINDABLE elements in a browser, and the page
     relies on it: renderHostCard writes a <button id="hostbtn"> into `box.innerHTML` and then
     `$("#hostbtn").addEventListener(...)` on the very next line. Without this the shim throws on
     its own scaffolding rather than on anything the page got wrong. Only ids are modelled -- they
     are the only thing this page ever looks up. */
  _adopt(h){
    for (const m of String(h).matchAll(/\bid=["']([\w-]+)["']/g)){
      const e = new El("div");
      e.id = m[1];
      e.parent = this;
      this.kids.push(e);
    }
  }
  append(...cs){ for (const c of cs){ if (c && c.tagName !== undefined) c.parent = this;
                                      this.kids.push(c); } }
  appendChild(c){ this.append(c); return c; }
  addEventListener(ev, fn){ (this.listeners[ev] = this.listeners[ev] || []).push(fn); }
  fire(ev){ for (const fn of (this.listeners[ev] || [])) fn({ target: this, closest: () => null }); }
  closest(){ return null; }
  querySelector(){ return null; }
}

const stripTags = s => String(s).replace(/<[^>]*>/g, " ");
const attached = n => { let p = n; while (p){ if (p._static) return true; p = p.parent; } return false; };

function text(n){
  if (n === null || n === undefined) return "";
  if (typeof n === "string") return n;
  return (stripTags(n._html) + " " + (n._text || "") + " " +
          n.kids.map(text).join(" ")).replace(/\s+/g, " ");
}

function makeDocument(staticIds){
  const doc = {
    createElement: t => new El(t),
    createTextNode: t => { const e = new El("#text"); e.textContent = t; return e; },
    getElementById: id => NODES.find(n => n.id === id && attached(n)) || null,
    querySelector: sel => {
      const m = /^#([\w-]+)$/.exec(String(sel));
      if (!m) return null;
      return NODES.find(n => n.id === m[1] && attached(n)) || null;
    },
    execCommand: () => true,
  };
  doc.body = new El("body"); doc.body._static = true;
  for (const id of staticIds){
    const e = new El("div"); e.id = id; e._static = true;
  }
  return doc;
}

module.exports = { El, makeDocument, text, attached, NODES };
