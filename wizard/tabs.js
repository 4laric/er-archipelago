/* tabs.js -- the site's tab strip, for the four pages that are not Jinja templates.
 *
 * WHAT THIS IS FOR. peliarch.ca is two kinds of page. /downloads, /hosting and /room/<id> are
 * templates that inherit their chrome from webgui/templates/base.html. landing.html, wizard.html,
 * checks.html and report.html are single files built HERE, installed at the stable tag by
 * tools/deploy_wizard.sh, and they never pass through Jinja -- so they cannot inherit anything.
 * Before this file the answer was to hand-copy the navigation into each one, which is four
 * surfaces to forget: landing.html already hand-copies the footer for exactly this reason and says
 * so in a comment asking the next person not to drop it.
 *
 * One file, four pages, one definition. Each page carries only
 *
 *     <div id="er-tabs" data-tab="builder"></div>
 *     <script src="/er/tabs.js" defer></script>
 *
 * !! ABSENCE MUST BE SILENT, AND THAT IS A REQUIREMENT RATHER THAN A NICETY. wizard.html also
 * ships as a file:// page inside every release zip. There, `/er/tabs.js` resolves to
 * file:///er/tabs.js and does not load -- so the placeholder stays empty, and it must therefore be
 * an empty div with no border, no reserved height and no "loading" text. It must also not be
 * missed: a strip of links to /downloads and /hosting would be dead on a file:// page anyway, so
 * not rendering it there is the correct outcome and not a degradation.
 *
 * !! THE OTHER COPY OF THIS STRIP IS IN ANOTHER REPO: peliarch's webgui/templates/base.html
 * renders the same six links server-side, because a templated page whose only navigation came
 * from a script that 404s on an undeployed box would have no navigation at all. That is a
 * deliberate two-copy trade, and both copies are pinned by a test: TestTabStrip in peliarch's
 * webgui/test_app.py, and tools/check_tabs.py here. Change a tab and both fail, loudly, in the
 * repo where the other half lives.
 *
 * Sentinel for deploy_wizard.sh's install_one: id="er-tabs-strip", which appears in the markup
 * built below.
 *
 * !! DO NOT NAME EITHER COUPLING MARKER IN THIS FILE, not even in a comment saying it has neither.
 * test_gf_publish_channels decides a page's release channel by GREPPING it for the option-surface
 * and data-stamp marker strings, so writing one down here made this file look coupled to a build
 * and knocked it off the --site fast path. It carries no option surface and no data stamp; the way
 * to say that is in these words, and the gate caught the first attempt at saying it in the others.
 */
(function () {
  "use strict";

  /* The BUILDER IS FIRST because it is what people arrive for: the only surface anyone can use
     before deciding whether to install a DLL. Hosting is a tab, not the front page. */
  var TABS = [
    ["builder",   "/er/",            "Builder"],
    ["downloads", "/downloads",      "Downloads"],
    ["hosting",   "/hosting",        "Hosting"],
    ["questlines", "/er/questlines.html", "Questlines"],
    ["checks",    "/er/checks.html", "Checks"],
    ["report",    "/er/report.html", "Report a bug"]
  ];

  var host = document.getElementById("er-tabs");
  if (!host) { return; }

  /* The page says which tab it is. Falling back to the URL keeps a page that forgot the attribute
     from rendering a strip with nothing marked -- but the attribute is authoritative, because
     /er/beta/wizard.html is still the builder and its path does not say so. */
  var current = host.getAttribute("data-tab") || "";
  if (!current) {
    var p = location.pathname;
    if (/\/er\/(beta\/)?(wizard\.html)?$/.test(p)) { current = "builder"; }
    else if (p.indexOf("checks") !== -1)           { current = "checks"; }
    else if (p.indexOf("report") !== -1)           { current = "report"; }
    else if (p.indexOf("questlines") !== -1)       { current = "questlines"; }
    else if (p.indexOf("downloads") !== -1)        { current = "downloads"; }
    else if (p.indexOf("hosting") !== -1)          { current = "hosting"; }
  }

  /* Palette comes from the pages' own :root variables, with fallbacks, so the strip is native on
     all four rather than a widget bolted onto them. */
  var css = document.createElement("style");
  css.textContent = [
    "#er-tabs-strip{display:flex;flex-wrap:wrap;gap:0;align-items:stretch;",
    "  border-bottom:1px solid var(--gold-dim,#8a7440);background:var(--bg2,#1c1917);",
    "  font:14px/1 Georgia,'Times New Roman',serif}",
    "#er-tabs-strip a{display:block;padding:12px 18px;text-decoration:none;",
    "  color:var(--dim,#9a8f78);letter-spacing:.06em;text-transform:uppercase;font-size:12.5px;",
    "  border-bottom:2px solid transparent;transition:.15s}",
    "#er-tabs-strip a:hover{color:var(--text,#e8e0cf);background:var(--panel,#232019)}",
    /* Marked with an underline, not just a brighter grey: "which page am I on" should not depend
       on telling two greys apart. */
    "#er-tabs-strip a.on{color:var(--gold,#c8a95a);border-bottom-color:var(--gold,#c8a95a)}",
    "#er-tabs-strip .sp{flex:1}",
    "@media(max-width:620px){#er-tabs-strip a{padding:10px 12px;font-size:11.5px}}"
  ].join("");
  document.head.appendChild(css);

  var html = ['<nav id="er-tabs-strip" aria-label="Site sections">'];
  for (var i = 0; i < TABS.length; i++) {
    var id = TABS[i][0], href = TABS[i][1], label = TABS[i][2];
    var on = (id === current);
    html.push(
      '<a href="' + href + '"' + (on ? ' class="on" aria-current="page"' : "") + '>' + label + "</a>"
    );
  }
  html.push('<span class="sp"></span>');
  html.push("</nav>");
  host.innerHTML = html.join("");
})();
