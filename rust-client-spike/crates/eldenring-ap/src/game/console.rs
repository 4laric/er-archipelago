//! Debug console (Windows) — ports the C++ client's interactive command window that the file-logging
//! Rust client dropped. Allocates a console and accepts `/setflag`, `/getflag`, `/region`, `/kill`,
//! `/help`. Commands are PARSED on a dedicated stdin thread and EXECUTED on the FrameBegin game tick
//! (event-flag access is game-thread-only — same rule as features.rs), with results printed back.
//!
//! Behind the `detour` feature (default) because it needs the `windows` crate (AllocConsole + the
//! Win32_System_Console surface). Lean `--no-default-features` builds compile it out.

#![allow(dead_code)]

use std::collections::VecDeque;
use std::fs::{File, OpenOptions};
use std::io::{BufRead, BufReader, Write};
use std::sync::{Mutex, OnceLock};

use super::flags;

/// Lines typed at the console, parsed on the stdin thread, drained on the game tick.
fn queue() -> &'static Mutex<VecDeque<String>> {
    static Q: OnceLock<Mutex<VecDeque<String>>> = OnceLock::new();
    Q.get_or_init(|| Mutex::new(VecDeque::new()))
}

/// The console output device (CONOUT$), opened once. `None` if it couldn't be opened.
fn conout() -> &'static Mutex<Option<File>> {
    static O: OnceLock<Mutex<Option<File>>> = OnceLock::new();
    O.get_or_init(|| Mutex::new(OpenOptions::new().write(true).open("CONOUT$").ok()))
}

/// Print a line to the console AND mirror it into the trace log (so console output is captured too).
fn say(s: &str) {
    if let Ok(mut g) = conout().lock() {
        if let Some(f) = g.as_mut() {
            let _ = writeln!(f, "{s}");
        }
    }
    tracing::info!("[console] {s}");
}

/// Called once from `game::init` (worker thread): allocate a console + spawn the stdin reader.
pub fn init() {
    use windows::Win32::System::Console::AllocConsole;
    // Best-effort: if the loader already gave the process a console, AllocConsole returns Err and we
    // simply reuse the existing one via CONOUT$/CONIN$.
    unsafe {
        let _ = AllocConsole();
    }
    say("eldenring-ap console ready. Commands:");
    say("  /setflag <id> <0|1>   set or clear an event flag");
    say("  /getflag <id>         read an event flag");
    say("  /region               print the player's PlayRegionId");
    say("  /kill                 set DeathLink kill flag 76996 (die, keep runes)");
    say("  /help                 this list");
    std::thread::spawn(reader_thread);
}

/// Blocking stdin loop on a dedicated thread. Reads from CONIN$ directly: after AllocConsole,
/// `std::io::stdin()` may still bind the old (absent) handle, so open the console input device.
fn reader_thread() {
    let conin = match OpenOptions::new().read(true).open("CONIN$") {
        Ok(f) => f,
        Err(e) => {
            say(&format!("console: cannot open CONIN$ ({e}); input disabled"));
            return;
        }
    };
    let mut reader = BufReader::new(conin);
    let mut line = String::new();
    loop {
        line.clear();
        match reader.read_line(&mut line) {
            Ok(0) => break, // console closed (EOF)
            Ok(_) => {
                let cmd = line.trim().to_string();
                if !cmd.is_empty() {
                    queue().lock().unwrap().push_back(cmd);
                }
            }
            Err(_) => break,
        }
    }
}

/// Called from `game::tick` (game thread): drain + execute queued commands. Event-flag reads/writes
/// are only safe on this thread, so every command effect runs here.
pub fn tick() {
    let cmds: Vec<String> = {
        let mut q = queue().lock().unwrap();
        if q.is_empty() {
            return;
        }
        q.drain(..).collect()
    };
    for cmd in cmds {
        exec(&cmd);
    }
}

fn exec(cmd: &str) {
    let p: Vec<&str> = cmd.split_whitespace().collect();
    match p.as_slice() {
        ["/setflag", id, val] => match (id.parse::<u32>(), parse_bool(val)) {
            (Ok(flag), Some(on)) => {
                let ok = flags::try_set_event_flag(flag, on);
                say(&format!(
                    "setflag {flag} = {} -> {}",
                    on as u8,
                    if ok { "ok" } else { "holder not ready (not in world?)" }
                ));
            }
            _ => say("usage: /setflag <id> <0|1>"),
        },
        ["/getflag", id] => match id.parse::<u32>() {
            Ok(flag) => say(&format!("getflag {flag} = {}", flags::get_event_flag(flag) as u8)),
            Err(_) => say("usage: /getflag <id>"),
        },
        ["/region"] => match flags::play_region_id() {
            Some(r) => say(&format!("play_region_id = {r}")),
            None => say("play_region_id = (not in world)"),
        },
        ["/kill"] => {
            let ok = flags::try_set_event_flag(76996, true);
            say(&format!(
                "/kill -> set DeathLink kill flag 76996 ({})",
                if ok { "ok" } else { "holder not ready (not in world?)" }
            ));
        }
        ["/help"] => say("commands: /setflag <id> <0|1>, /getflag <id>, /region, /kill, /help"),
        _ => say(&format!("unknown command: '{cmd}' (try /help)")),
    }
}

fn parse_bool(s: &str) -> Option<bool> {
    match s {
        "1" | "on" | "true" | "ON" | "TRUE" => Some(true),
        "0" | "off" | "false" | "OFF" | "FALSE" => Some(false),
        _ => None,
    }
}
