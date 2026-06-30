//! fmg_inject.rs — name the synthetic AP goods by rebuilding the GoodsName MsgData (FMG entry
//! injection, allocate-extend-swap). STAGED by `MODE`; see FMG-INJECTION-PLAN.md.
//!   MODE_PARSE (0):    READ-ONLY parse + cross-check vs SearchStringTable.            [proven]
//!   MODE_IDENTITY (1): rebuild an IDENTICAL block, self-validate, swap base_array[0][10].
//!   MODE_INJECT (2):   identity + add synthetic-good entries (next stage).
//!
//! MsgData layout (RE'd from 0x266DC90): +0x0C u32 groupCount ; +0x18 u64* stringOffsetTable
//! (MsgData-relative offsets) ; +0x28 GroupRecord[count] 16B each {u32 stringIndexBase,u32 firstId,
//! u32 lastId,u32 pad}. stringIndex=(id-firstId)+stringIndexBase ; off=offsetTable[idx] ;
//! str=MsgData+off (0=>missing). repo @ base+0x3D7D4F8 ; base_array[0][10]=GoodsName MsgData ;
//! SearchStringTable @ base+0x266D3C0 (repo,group=0,category,id)->wchar*.
//!
//! SAFETY: the rebuilt block is validated in OUR memory (re-lookup the check ids) BEFORE the swap; a
//! build mismatch aborts the swap (game untouched). The new block is VirtualAlloc'd RW and leaked for
//! the process. Identity stage makes NO visible change if correct — that's the proof.

use std::collections::HashMap;
use std::ffi::c_void;
use std::sync::atomic::{AtomicBool, Ordering};

const REPO_RVA: usize = 0x3D7D4F8;
const SEARCH_RVA: usize = 0x266D3C0;
const SEARCH_SIG: &[u8] = &[
    0x3B, 0x51, 0x10, 0x73, 0x29, 0x44, 0x3B, 0x41, 0x14, 0x73, 0x23, 0x48, 0x8B, 0x41, 0x08,
];
const GOODS_CATEGORY: u32 = 10;

const MD_GROUPCOUNT: usize = 0x0C;
const MD_OFFTABLE_PTR: usize = 0x18;
const MD_GROUPS: usize = 0x28;
// Upper bound on how many UTF-16 units `read_units` will copy before giving up looking for the NUL.
// FMG strings are always NUL-terminated, so this only caps pathological/unterminated reads — but it
// MUST exceed the longest real string we copy. 128 was fine for GoodsName (short item names) but
// TRUNCATES vanilla GoodsCaption/Info (lore boxes run many hundreds of units); 4096 covers captions.
const STR_CAP: usize = 4096;

// sub[] category index for GoodsCaption (the big lore box). PINNED 2026-06-30 via the fmg_probe
// slot-map dump: for id 150, sub[10]=name "Furlcalling Finger Remedy", sub[20]=GoodsInfo short line
// "Reveals co-op and hostile summoning signs", sub[24]=the multi-line lore caption "Item for online
// play.\n(Can also be used...". So GoodsCaption = category 24. (GoodsInfo = 20 if we ever want the
// short line too.) >=0 enables `run_descriptions`.
const GOODS_CAPTION_CATEGORY: i32 = 24;

const MODE_PARSE: u8 = 0;
#[allow(dead_code)]
const MODE_IDENTITY: u8 = 1;
const MODE_INJECT: u8 = 2;
const MODE: u8 = MODE_INJECT;

const CHECK_IDS: &[u32] = &[100, 101, 109, 110, 115, 150, 8000, 10100];

type SearchFn = unsafe extern "C" fn(*mut c_void, u32, u32, u32) -> *const u16;

static DONE: AtomicBool = AtomicBool::new(false);

#[derive(Clone, Copy)]
struct Group {
    string_index_base: u32,
    first_id: u32,
    last_id: u32,
}

fn plausible(p: usize) -> bool {
    p >= 0x10000 && p < 0x7FFF_FFFF_FFFF
}
fn current_module_base() -> Option<usize> {
    use windows::Win32::System::LibraryLoader::GetModuleHandleW;
    let h = unsafe { GetModuleHandleW(None) }.ok()?;
    Some(h.0 as usize)
}
unsafe fn read_u32(a: usize) -> u32 {
    (a as *const u32).read_unaligned()
}
unsafe fn read_u64(a: usize) -> u64 {
    (a as *const u64).read_unaligned()
}
unsafe fn read_usize(a: usize) -> usize {
    (a as *const usize).read_unaligned()
}
unsafe fn write_u64(a: usize, v: u64) {
    (a as *mut u64).write_unaligned(v);
}
unsafe fn write_u16(a: usize, v: u16) {
    (a as *mut u16).write_unaligned(v);
}
unsafe fn read_units(ptr: usize) -> Vec<u16> {
    let mut v = Vec::new();
    for i in 0..STR_CAP {
        let c = (ptr as *const u16).add(i).read_unaligned();
        if c == 0 {
            break;
        }
        v.push(c);
    }
    v
}
fn read_string(ptr: usize) -> Option<String> {
    if !plausible(ptr) {
        return None;
    }
    let u = unsafe { read_units(ptr) };
    if u.is_empty() {
        None
    } else {
        Some(String::from_utf16_lossy(&u))
    }
}
fn sig_ok(addr: usize) -> bool {
    let b = unsafe { std::slice::from_raw_parts(addr as *const u8, SEARCH_SIG.len()) };
    b == SEARCH_SIG
}

unsafe fn goods_msgdata(base: usize) -> Option<usize> {
    let repo = read_usize(base + REPO_RVA);
    if !plausible(repo) {
        return None;
    }
    let base_arr = read_usize(repo + 0x08);
    if !plausible(base_arr) {
        return None;
    }
    let sub = read_usize(base_arr);
    if !plausible(sub) {
        return None;
    }
    let md = read_usize(sub + GOODS_CATEGORY as usize * 8);
    if plausible(md) {
        Some(md)
    } else {
        None
    }
}

unsafe fn parse(md: usize) -> Option<(Vec<Group>, Vec<u64>)> {
    let count = read_u32(md + MD_GROUPCOUNT) as usize;
    if count == 0 || count > 0x10000 {
        return None;
    }
    let mut groups = Vec::with_capacity(count);
    let mut num_strings: u32 = 0;
    for i in 0..count {
        let g = md + MD_GROUPS + i * 16;
        let sib = read_u32(g);
        let fi = read_u32(g + 4);
        let li = read_u32(g + 8);
        if li < fi || li.saturating_sub(fi) > 0x10_0000 {
            return None;
        }
        groups.push(Group { string_index_base: sib, first_id: fi, last_id: li });
        num_strings = num_strings.max(sib.saturating_add(li - fi).saturating_add(1));
    }
    if num_strings == 0 || num_strings > 0x20_0000 {
        return None;
    }
    let offtab = read_usize(md + MD_OFFTABLE_PTR);
    if !plausible(offtab) {
        return None;
    }
    let mut offsets = Vec::with_capacity(num_strings as usize);
    for s in 0..num_strings as usize {
        offsets.push(read_u64(offtab + s * 8));
    }
    Some((groups, offsets))
}

fn my_lookup(md: usize, groups: &[Group], offsets: &[u64], id: u32) -> Option<String> {
    let g = groups.iter().find(|g| id >= g.first_id && id <= g.last_id)?;
    let si = (id - g.first_id + g.string_index_base) as usize;
    let off = *offsets.get(si)?;
    if off == 0 {
        return None;
    }
    read_string(md + off as usize)
}

unsafe fn valloc(size: usize) -> Option<usize> {
    use windows::Win32::System::Memory::{VirtualAlloc, MEM_COMMIT, MEM_RESERVE, PAGE_READWRITE};
    let p = VirtualAlloc(None, size, MEM_COMMIT | MEM_RESERVE, PAGE_READWRITE);
    if p.is_null() {
        None
    } else {
        Some(p as usize) // VirtualAlloc memory is zero-initialized
    }
}

unsafe fn write_u32(a: usize, v: u32) {
    (a as *mut u32).write_unaligned(v);
}

/// Build a fresh MsgData block = vanilla content + one new single-id group per `injects` entry
/// (`injects` MUST be sorted by id, and all ids > every vanilla id so group order stays ascending).
/// Header copied verbatim; groups + offset table + (deduped vanilla + injected) string data are laid
/// out fresh, all base-relative. `injects` empty => exact identity rebuild. Returns the new block.
unsafe fn build_block(
    vanilla: usize,
    groups: &[Group],
    offsets: &[u64],
    injects: &[(u32, Vec<u16>)],
    overrides: &[(u32, Vec<u16>)],
) -> Option<usize> {
    let num_vanilla = offsets.len();
    let num_out = num_vanilla + injects.len();
    // Overrides REPLACE the string of an EXISTING id (no new string-index slot): resolve each id to its
    // string index via the vanilla groups; ids not in any group are skipped. The redirect + the appended
    // override string happen below. (si -> new units)
    let mut ovr: Vec<(usize, &Vec<u16>)> = Vec::new();
    for (id, s) in overrides {
        if let Some(g) = groups.iter().find(|g| *id >= g.first_id && *id <= g.last_id) {
            ovr.push(((*id - g.first_id + g.string_index_base) as usize, s));
        }
    }
    // Merge contiguous inject ids into RUNS -> one group per run (sorted; ids > all vanilla ids). This
    // keeps groups few + non-overlapping so the game's binary search is boundary-safe (4777 single-id
    // groups created an edge case on the lowest ids). String indices stay sequential per inject.
    let mut inj_groups: Vec<Group> = Vec::new();
    let mut k = 0usize;
    while k < injects.len() {
        let start = injects[k].0;
        let base_idx = (num_vanilla + k) as u32;
        let mut end = start;
        let mut j = k;
        while j + 1 < injects.len() && injects[j + 1].0 == injects[j].0 + 1 {
            j += 1;
            end = injects[j].0;
        }
        inj_groups.push(Group { string_index_base: base_idx, first_id: start, last_id: end });
        k = j + 1;
    }
    let count = groups.len() + inj_groups.len();
    let offtab_off = ((MD_GROUPS + count * 16) + 7) & !7;
    let strings_off = ((offtab_off + num_out * 8) + 1) & !1;

    // dedup vanilla strings by offset (multiple ids may share one string)
    let mut uniq_units: Vec<Vec<u16>> = Vec::new();
    let mut map: HashMap<u64, usize> = HashMap::new();
    for &off in offsets {
        if off == 0 || map.contains_key(&off) {
            continue;
        }
        map.insert(off, uniq_units.len());
        uniq_units.push(read_units(vanilla + off as usize));
    }
    let uniq_bytes: usize = uniq_units.iter().map(|s| (s.len() + 1) * 2).sum();
    let inj_bytes: usize = injects.iter().map(|(_, s)| (s.len() + 1) * 2).sum();
    let ovr_bytes: usize = ovr.iter().map(|(_, s)| (s.len() + 1) * 2).sum();
    let total = strings_off + uniq_bytes + inj_bytes + ovr_bytes;

    let block = valloc(total)?;
    // header (0..0x28) verbatim
    std::ptr::copy_nonoverlapping(vanilla as *const u8, block as *mut u8, MD_GROUPS);
    // group records: vanilla, then one single-id group per inject (stringIndexBase = num_vanilla + i)
    for (i, g) in groups.iter().enumerate() {
        let gr = block + MD_GROUPS + i * 16;
        write_u32(gr, g.string_index_base);
        write_u32(gr + 4, g.first_id);
        write_u32(gr + 8, g.last_id);
        write_u32(gr + 12, 0);
    }
    for (i, g) in inj_groups.iter().enumerate() {
        let gr = block + MD_GROUPS + (groups.len() + i) * 16;
        write_u32(gr, g.string_index_base);
        write_u32(gr + 4, g.first_id);
        write_u32(gr + 8, g.last_id);
        write_u32(gr + 12, 0);
    }
    write_u32(block + MD_GROUPCOUNT, count as u32);

    // strings: deduped vanilla (record new offsets), then injected names
    let mut wpos = strings_off;
    let mut uniq_off: Vec<u64> = Vec::with_capacity(uniq_units.len());
    for s in &uniq_units {
        let dst = block + wpos;
        for (i, &u) in s.iter().enumerate() {
            write_u16(dst + i * 2, u);
        }
        write_u16(dst + s.len() * 2, 0);
        uniq_off.push(wpos as u64);
        wpos += (s.len() + 1) * 2;
    }
    let mut inj_off: Vec<u64> = Vec::with_capacity(injects.len());
    for (_, s) in injects {
        let dst = block + wpos;
        for (i, &u) in s.iter().enumerate() {
            write_u16(dst + i * 2, u);
        }
        write_u16(dst + s.len() * 2, 0);
        inj_off.push(wpos as u64);
        wpos += (s.len() + 1) * 2;
    }
    // override strings: appended after the injected strings; record the new offset per overridden
    // string index so the offset table below can redirect that id to its longer string.
    let mut ovr_off: HashMap<usize, u64> = HashMap::new();
    for (si, s) in &ovr {
        let dst = block + wpos;
        for (i, &u) in s.iter().enumerate() {
            write_u16(dst + i * 2, u);
        }
        write_u16(dst + s.len() * 2, 0);
        ovr_off.insert(*si, wpos as u64);
        wpos += (s.len() + 1) * 2;
    }
    // offset table: vanilla indices (relocated), redirecting any overridden index to its new string,
    // then injected indices.
    for (s, &off) in offsets.iter().enumerate() {
        let v = if let Some(&o) = ovr_off.get(&s) {
            o
        } else if off == 0 {
            0
        } else {
            uniq_off[map[&off]]
        };
        write_u64(block + offtab_off + s * 8, v);
    }
    for (i, &off) in inj_off.iter().enumerate() {
        write_u64(block + offtab_off + (num_vanilla + i) * 8, off);
    }
    write_u64(block + MD_OFFTABLE_PTR, (block + offtab_off) as u64);
    Some(block)
}

unsafe fn swap_goods(base: usize, newblock: usize) -> bool {
    let repo = read_usize(base + REPO_RVA);
    let base_arr = read_usize(repo + 0x08);
    let sub = read_usize(base_arr);
    if !plausible(sub) {
        return false;
    }
    let slot = sub + GOODS_CATEGORY as usize * 8; // &base_array[0][10]
    (slot as *mut usize).write_unaligned(newblock);
    true
}

/// Resolve `base_array[0][category]` (the MsgData* for an arbitrary FMG category). Generalization of
/// `goods_msgdata` for the caption path; `category_msgdata(base, GOODS_CATEGORY) == goods_msgdata`.
unsafe fn category_msgdata(base: usize, category: u32) -> Option<usize> {
    let repo = read_usize(base + REPO_RVA);
    if !plausible(repo) {
        return None;
    }
    let base_arr = read_usize(repo + 0x08);
    if !plausible(base_arr) {
        return None;
    }
    let sub = read_usize(base_arr);
    if !plausible(sub) {
        return None;
    }
    let md = read_usize(sub + category as usize * 8);
    if plausible(md) {
        Some(md)
    } else {
        None
    }
}

/// Atomically point `base_array[0][category]` at a freshly-built block. Generalization of `swap_goods`.
unsafe fn swap_category(base: usize, category: u32, newblock: usize) -> bool {
    let repo = read_usize(base + REPO_RVA);
    let base_arr = read_usize(repo + 0x08);
    let sub = read_usize(base_arr);
    if !plausible(sub) {
        return false;
    }
    let slot = sub + category as usize * 8;
    (slot as *mut usize).write_unaligned(newblock);
    true
}

/// Inject GoodsCaption (the big lore box) entries for the synthetic AP goods — the SAME
/// allocate-extend-swap as `run()`, but into the caption category instead of GoodsName, and reusing
/// the proven `build_block` / `parse` / `my_lookup` helpers so the confirmed name path is untouched.
///
/// `descriptions` = `(synthetic_id, utf16_caption)` pairs built by the caller from the scout cache via
/// `er_logic::name_override::description(game, owner, slot, kind)` — the same per-id data that feeds
/// the real name. Ids must be the synthetic goods ids (all > every vanilla caption id); this sorts
/// them so the appended groups stay ascending for the game's binary search.
///
/// Safe by construction:
///   * no-op (returns `true`) while `GOODS_CAPTION_CATEGORY` is unpinned (< 0) — cannot corrupt;
///   * no-op while `descriptions` is empty (scout cache not filled yet) — retry next tick;
///   * the rebuilt block is validated in OUR memory (vanilla sample round-trips + every injected id
///     resolves) BEFORE the swap; any mismatch aborts the swap and leaves the game untouched.
#[allow(dead_code)] // wired from tick() once the scout cache (game/owner/slot/flags per synth id) lands
pub fn run_descriptions(descriptions: &[(u32, Vec<u16>)]) -> bool {
    if GOODS_CAPTION_CATEGORY < 0 {
        tracing::warn!(
            "FMG-inject(caption): GOODS_CAPTION_CATEGORY unpinned; skipping (pin the sub[] index first)"
        );
        return true;
    }
    if descriptions.is_empty() {
        return true; // nothing to inject yet (scout cache not filled) — cheap retry next tick
    }
    let category = GOODS_CAPTION_CATEGORY as u32;
    let base = match current_module_base() {
        Some(b) => b,
        None => return true,
    };
    let md = match unsafe { category_msgdata(base, category) } {
        Some(m) => m,
        None => return false, // repo/category not up yet — retry next tick
    };
    let (groups, offsets) = match unsafe { parse(md) } {
        Some(p) => p,
        None => {
            tracing::warn!("FMG-inject(caption): parse failed");
            return true;
        }
    };

    // build_block requires injects sorted by id, all ids > every vanilla id (synthetic ids are > 3.78M
    // > vanilla caption ids, so appending keeps the group list ascending / binary-search-safe).
    let mut injects: Vec<(u32, Vec<u16>)> = descriptions.to_vec();
    injects.sort_by_key(|(id, _)| *id);

    let block = match unsafe { build_block(md, &groups, &offsets, &injects, &[]) } {
        Some(b) => b,
        None => {
            tracing::warn!("FMG-inject(caption): build_block failed (alloc?)");
            return true;
        }
    };
    let (g2, o2) = match unsafe { parse(block) } {
        Some(p) => p,
        None => {
            tracing::warn!("FMG-inject(caption): rebuilt block failed re-parse; NOT swapping");
            return true;
        }
    };

    // Validate in our own memory before the swap: a sample of vanilla caption ids must round-trip
    // unchanged, and every injected id must resolve to exactly what we wrote.
    let mut mismatch = 0;
    for g in groups.iter().take(8) {
        let id = g.first_id;
        if my_lookup(md, &groups, &offsets, id) != my_lookup(block, &g2, &o2, id) {
            mismatch += 1;
        }
    }
    for (id, s) in injects.iter() {
        let want = String::from_utf16_lossy(s);
        if my_lookup(block, &g2, &o2, *id).as_deref() != Some(want.as_str()) {
            mismatch += 1;
        }
    }
    if mismatch != 0 {
        tracing::warn!(
            "FMG-inject(caption): rebuilt block mismatch on {mismatch} id(s); NOT swapping (safe)"
        );
        return true;
    }

    tracing::info!(
        "FMG-inject(caption): validated (+{} descriptions); swapping caption sub[{category}] -> {block:#x}",
        injects.len()
    );
    unsafe { swap_category(base, category, block) };
    true
}

/// Resolve each synthetic goods id to (real name, optional caption) via the scout cache, joined by the
/// row's vagrant-encoded AP location id (`er_codec::recombine_location_id`). Cache miss => "AP#<id>"
/// name and no caption. Returns (GoodsName injects, GoodsCaption injects).
fn resolve_synth_injects(ids: &[u32]) -> (Vec<(u32, Vec<u16>)>, Vec<(u32, Vec<u16>)>) {
    let mut names = Vec::with_capacity(ids.len());
    let mut caps = Vec::new();
    for &id in ids {
        let mut name = format!("AP#{id}");
        if let Some(f) = super::params::goods_row_fields(id as i32) {
            let loc = er_codec::recombine_location_id(
                f.vagrant_item_lot_id,
                f.vagrant_bonus_ene_drop_item_lot_id,
            );
            if let Some(s) = super::scout_proof::lookup(loc) {
                name = s.name.clone();
                let cap = er_logic::name_override::description(&s.game, &s.owner, s.slot, s.kind);
                caps.push((id, cap.encode_utf16().collect::<Vec<u16>>()));
            }
        }
        names.push((id, name.encode_utf16().collect::<Vec<u16>>()));
    }
    (names, caps)
}

/// Extend-swap OVERRIDES: replace the strings of EXISTING ids in `base_array[0][category]` with longer
/// AP strings, rebuilding from the LIVE block so any prior swap (e.g. this module's synthetic-goods
/// appends) is preserved. Used by shop_preview for names/info/captions that don't fit the packed vanilla
/// entry in place. Validated in OUR memory before the swap (a sample of non-overridden ids round-trips +
/// every override resolves to exactly what we wrote); any mismatch aborts (game untouched). No-op on
/// empty / category-not-up. Returns how many overrides landed.
pub fn extend_swap_overrides(category: u32, overrides: &[(u32, Vec<u16>)]) -> usize {
    if overrides.is_empty() {
        return 0;
    }
    let base = match current_module_base() {
        Some(b) => b,
        None => return 0,
    };
    let md = match unsafe { category_msgdata(base, category) } {
        Some(m) => m,
        None => return 0, // repo/category not up yet — caller retries next tick
    };
    let (groups, offsets) = match unsafe { parse(md) } {
        Some(p) => p,
        None => {
            tracing::warn!("FMG extend-swap(cat {category}): parse failed");
            return 0;
        }
    };
    // keep only ids that exist in a group (others have no slot to redirect)
    let resolvable: Vec<(u32, Vec<u16>)> = overrides
        .iter()
        .filter(|(id, _)| groups.iter().any(|g| *id >= g.first_id && *id <= g.last_id))
        .cloned()
        .collect();
    if resolvable.is_empty() {
        return 0;
    }
    let block = match unsafe { build_block(md, &groups, &offsets, &[], &resolvable) } {
        Some(b) => b,
        None => {
            tracing::warn!("FMG extend-swap(cat {category}): build_block failed (alloc?)");
            return 0;
        }
    };
    let (g2, o2) = match unsafe { parse(block) } {
        Some(p) => p,
        None => {
            tracing::warn!("FMG extend-swap(cat {category}): rebuilt block failed re-parse; NOT swapping");
            return 0;
        }
    };
    let ovr_ids: std::collections::HashSet<u32> = resolvable.iter().map(|(id, _)| *id).collect();
    let mut mismatch = 0;
    for g in groups.iter().take(16) {
        let id = g.first_id;
        if ovr_ids.contains(&id) {
            continue; // overridden on purpose; checked below
        }
        if my_lookup(md, &groups, &offsets, id) != my_lookup(block, &g2, &o2, id) {
            mismatch += 1;
        }
    }
    for (id, s) in &resolvable {
        let want = String::from_utf16_lossy(s);
        if my_lookup(block, &g2, &o2, *id).as_deref() != Some(want.as_str()) {
            mismatch += 1;
        }
    }
    if mismatch != 0 {
        tracing::warn!(
            "FMG extend-swap(cat {category}): rebuilt block mismatch on {mismatch} id(s); NOT swapping (safe)"
        );
        return 0;
    }
    unsafe { swap_category(base, category, block) };
    tracing::info!("FMG extend-swap(cat {category}): swapped (+{} overrides)", resolvable.len());
    resolvable.len()
}

pub fn run() -> bool {
    if DONE.load(Ordering::Relaxed) {
        return true;
    }
    let base = match current_module_base() {
        Some(b) => b,
        None => return true,
    };
    let md = match unsafe { goods_msgdata(base) } {
        Some(m) => m,
        None => return false,
    };
    let search_addr = base + SEARCH_RVA;
    if !sig_ok(search_addr) {
        tracing::warn!("FMG-inject: SearchStringTable sig mismatch; abort");
        return true;
    }
    let search: SearchFn = unsafe { std::mem::transmute::<usize, SearchFn>(search_addr) };
    let repo = unsafe { read_usize(base + REPO_RVA) } as *mut c_void;

    let (groups, offsets) = match unsafe { parse(md) } {
        Some(p) => p,
        None => {
            tracing::warn!("FMG-inject: parse failed");
            return true;
        }
    };
    tracing::info!(
        "FMG-inject: GoodsName md={md:#x} groups={} offsetTableLen={} (MODE={MODE})",
        groups.len(),
        offsets.len()
    );

    if MODE == MODE_PARSE {
        let mut ok = 0;
        for &id in CHECK_IDS {
            let mine = my_lookup(md, &groups, &offsets, id);
            let theirs = read_string(unsafe { search(repo, 0, GOODS_CATEGORY, id) as usize });
            let m = if mine == theirs { ok += 1; "MATCH" } else { "MISMATCH" };
            tracing::info!("FMG-inject:   id={id} mine={mine:?} game={theirs:?} [{m}]");
        }
        tracing::info!("FMG-inject: === parse {ok}/{} match ===", CHECK_IDS.len());
        DONE.store(true, Ordering::Relaxed);
        return true;
    }

    // MODE_IDENTITY / MODE_INJECT: build a fresh block, validate it in OUR memory, then swap.
    // For MODE_INJECT, names + captions are resolved from the scout cache (joined to each synthetic row
    // by its vagrant-encoded AP location id); a cache miss falls back to "AP#<id>" / no caption.
    let mut descs: Vec<(u32, Vec<u16>)> = Vec::new();
    let injects: Vec<(u32, Vec<u16>)> = if MODE == MODE_INJECT {
        let ids = super::params::synthetic_goods_ids();
        // Wait for the scout reply before naming so we get real names, not AP#<id>. No synthetics =>
        // nothing to wait for; proceed and inject nothing (solo/base-game).
        if !ids.is_empty() && !super::scout_proof::cache_ready() {
            return false; // retry next tick once LocationScouts has populated the cache
        }
        let (names, caps) = resolve_synth_injects(&ids);
        tracing::info!(
            "FMG-inject: {} synthetic goods ids; {} resolved to real name+caption from scout cache (rest -> AP#<id>)",
            ids.len(),
            caps.len()
        );
        descs = caps;
        names
    } else {
        Vec::new()
    };

    let block = match unsafe { build_block(md, &groups, &offsets, &injects, &[]) } {
        Some(b) => b,
        None => {
            tracing::warn!("FMG-inject: build_block failed (alloc?)");
            DONE.store(true, Ordering::Relaxed);
            return true;
        }
    };
    let (g2, o2) = match unsafe { parse(block) } {
        Some(p) => p,
        None => {
            tracing::warn!("FMG-inject: rebuilt block failed re-parse; NOT swapping");
            DONE.store(true, Ordering::Relaxed);
            return true;
        }
    };
    let mut mismatch = 0;
    for &id in CHECK_IDS {
        if my_lookup(md, &groups, &offsets, id) != my_lookup(block, &g2, &o2, id) {
            mismatch += 1;
        }
    }
    for (id, name) in injects.iter().take(4) {
        let want = String::from_utf16_lossy(name);
        let got = my_lookup(block, &g2, &o2, *id);
        let good = got.as_deref() == Some(want.as_str());
        tracing::info!("FMG-inject:   synth-check id={id} want={want:?} got={got:?} [{}]", if good { "OK" } else { "BAD" });
        if !good {
            mismatch += 1;
        }
    }
    if mismatch != 0 {
        tracing::warn!("FMG-inject: rebuilt block mismatch on {mismatch} id(s); NOT swapping (safe)");
        DONE.store(true, Ordering::Relaxed);
        return true;
    }
    tracing::info!("FMG-inject: block validated (+{} injected); swapping GoodsName -> {block:#x}", injects.len());
    if unsafe { swap_goods(base, block) } {
        for &id in CHECK_IDS {
            let theirs = read_string(unsafe { search(repo, 0, GOODS_CATEGORY, id) as usize });
            tracing::info!("FMG-inject:   post-swap vanilla id={id} game={theirs:?}");
        }
        for (id, _) in injects.iter().take(4) {
            let theirs = read_string(unsafe { search(repo, 0, GOODS_CATEGORY, *id) as usize });
            tracing::info!("FMG-inject:   post-swap SYNTH id={id} game={theirs:?}");
        }
        tracing::info!("FMG-inject: === GoodsName swap done (MODE={MODE}); synthetic goods named ===");
    }
    // GoodsCaption (cat 24): write each resolved synthetic good's description (game / owner / class).
    // Independent allocate-extend-swap; no-op if nothing resolved (e.g. solo seed) or category unpinned.
    if MODE == MODE_INJECT && !descs.is_empty() {
        run_descriptions(&descs);
    }
    DONE.store(true, Ordering::Relaxed);
    true
}
