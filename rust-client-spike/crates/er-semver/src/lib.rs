//! Pre-release-aware semver range check for the `versions` lockstep contract — Rust port of
//! `er_version_check.h`.
//!
//! The client receives a `versions` range over the AP protocol and must accept/reject its own
//! contract version against it. Implemented explicitly to node-semver semantics rather than the
//! `semver` crate, because the load-bearing rule below isn't replicated by Cargo semantics.
//!
//! THE RULE (node-semver, `includePrerelease = false`): a version carrying a pre-release tag
//! satisfies a range only if some comparator in the set shares its exact `[major, minor, patch]`
//! AND also carries a pre-release. This is why a naive `>=0.1.0` rejects `0.1.0-beta.1`, and why
//! `includePrerelease` must stay OFF (it would let a future-breaking `0.2.0-beta.1` leak through
//! `>=0.1.0 <0.2.0`).
//!
//! Lockstep phase emits e.g. `">=0.1.0-beta.1 <0.1.0-beta.2"`; graduates to `">=0.1.0 <0.2.0"` at
//! freeze. Acceptance vectors (verified against node-semver) live in the tests below.

use std::cmp::Ordering;

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SemVer {
    pub major: u64,
    pub minor: u64,
    pub patch: u64,
    /// dot-separated ids; empty => release
    pub prerelease: Vec<String>,
}

impl SemVer {
    pub fn has_pre(&self) -> bool {
        !self.prerelease.is_empty()
    }
    pub fn same_core(&self, o: &SemVer) -> bool {
        self.major == o.major && self.minor == o.minor && self.patch == o.patch
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ParseError(pub String);

impl std::fmt::Display for ParseError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}", self.0)
    }
}
impl std::error::Error for ParseError {}

fn split_dots(s: &str) -> Vec<String> {
    s.split('.').map(|p| p.to_string()).collect()
}

fn is_numeric_id(s: &str) -> bool {
    !s.is_empty() && s.bytes().all(|c| c.is_ascii_digit())
}

pub fn parse_semver(input: &str) -> Result<SemVer, ParseError> {
    // strip build metadata
    let s = input.split('+').next().unwrap_or(input);

    let (core, pre) = match s.split_once('-') {
        Some((core, pre)) => (core, Some(pre)),
        None => (s, None),
    };
    let parts: Vec<&str> = core.split('.').collect();
    if parts.len() != 3 {
        return Err(ParseError(format!("bad semver core: {input}")));
    }
    let parse_num = |p: &str| -> Result<u64, ParseError> {
        p.parse::<u64>()
            .map_err(|_| ParseError(format!("bad semver core: {input}")))
    };
    Ok(SemVer {
        major: parse_num(parts[0])?,
        minor: parse_num(parts[1])?,
        patch: parse_num(parts[2])?,
        prerelease: pre.map(split_dots).unwrap_or_default(),
    })
}

/// pre-release precedence (port of `comparePre`).
fn compare_pre(a: &[String], b: &[String]) -> Ordering {
    match (a.is_empty(), b.is_empty()) {
        (true, true) => return Ordering::Equal,
        (true, false) => return Ordering::Greater, // release > pre-release
        (false, true) => return Ordering::Less,
        (false, false) => {}
    }
    let n = a.len().min(b.len());
    for i in 0..n {
        let (x, y) = (&a[i], &b[i]);
        let (xn, yn) = (is_numeric_id(x), is_numeric_id(y));
        if xn && yn {
            // both numeric; node-semver compares numerically
            let xv: u64 = x.parse().unwrap();
            let yv: u64 = y.parse().unwrap();
            if xv != yv {
                return xv.cmp(&yv);
            }
        } else if xn != yn {
            // numeric ids rank below alphanumeric
            return if xn { Ordering::Less } else { Ordering::Greater };
        } else if x != y {
            return x.cmp(y);
        }
    }
    // fewer fields ranks lower
    a.len().cmp(&b.len())
}

pub fn compare_semver(a: &SemVer, b: &SemVer) -> Ordering {
    a.major
        .cmp(&b.major)
        .then_with(|| a.minor.cmp(&b.minor))
        .then_with(|| a.patch.cmp(&b.patch))
        .then_with(|| compare_pre(&a.prerelease, &b.prerelease))
}

#[derive(Debug, Clone, PartialEq, Eq)]
enum Op {
    Gte,
    Gt,
    Lte,
    Lt,
    Eq,
}

#[derive(Debug, Clone)]
struct Comparator {
    op: Op,
    ver: SemVer,
}

/// Whitespace-separated comparators (single AND set; no `||`), each `<op><version>`, op in
/// `{ >=, <=, >, <, = }`; a bare version means `=`. (Port of `parseRange`.)
fn parse_range(range: &str) -> Result<Vec<Comparator>, ParseError> {
    let mut out = Vec::new();
    for tok in range.split_whitespace() {
        let (op, v) = if let Some(rest) = tok.strip_prefix(">=") {
            (Op::Gte, rest)
        } else if let Some(rest) = tok.strip_prefix("<=") {
            (Op::Lte, rest)
        } else if let Some(rest) = tok.strip_prefix('>') {
            (Op::Gt, rest)
        } else if let Some(rest) = tok.strip_prefix('<') {
            (Op::Lt, rest)
        } else if let Some(rest) = tok.strip_prefix('=') {
            (Op::Eq, rest)
        } else {
            (Op::Eq, tok)
        };
        out.push(Comparator {
            op,
            ver: parse_semver(v)?,
        });
    }
    Ok(out)
}

fn apply_op(cmp: Ordering, op: &Op) -> bool {
    match op {
        Op::Gte => cmp != Ordering::Less,
        Op::Gt => cmp == Ordering::Greater,
        Op::Lte => cmp != Ordering::Greater,
        Op::Lt => cmp == Ordering::Less,
        Op::Eq => cmp == Ordering::Equal,
    }
}

/// node-semver `satisfies`, `includePrerelease = false`. Returns `Err` if either string fails to
/// parse (the C++ version throws; the connect path should treat a parse error as "reject").
pub fn version_satisfies(version_str: &str, range_str: &str) -> Result<bool, ParseError> {
    let v = parse_semver(version_str)?;
    let comps = parse_range(range_str)?;
    for c in &comps {
        if !apply_op(compare_semver(&v, &c.ver), &c.op) {
            return Ok(false);
        }
    }
    if v.has_pre() {
        // the pre-release-in-range gate
        let allowed = comps.iter().any(|c| c.ver.has_pre() && c.ver.same_core(&v));
        if !allowed {
            return Ok(false);
        }
    }
    Ok(true)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn sat(v: &str, r: &str) -> bool {
        version_satisfies(v, r).expect("parse")
    }

    #[test]
    fn satisfies_vectors_match_node_semver() {
        // Mirrors tests.cpp::test_versions, verified against node-semver v22.
        let l = ">=0.1.0-beta.1 <0.1.0-beta.2"; // lockstep now
        let g = ">=0.1.0 <0.2.0"; // graduated at freeze
        let n = ">=0.1.0"; // naive trap
        let cases: &[(&str, &str, bool)] = &[
            ("0.1.0-beta.1", l, true),
            ("0.1.0-beta.2", l, false),
            ("0.1.0", l, false),
            ("0.2.0-beta.1", l, false),
            ("0.2.0", l, false),
            ("0.1.0-beta.1", g, false), // the trap: hardcoding graduated form rejects beta.1
            ("0.1.0", g, true),
            ("0.2.0-beta.1", g, false), // future-breaking prerelease does NOT leak
            ("0.2.0", g, false),
            ("0.1.0-beta.1", n, false), // gotcha: plain >=0.1.0 rejects matching beta.1
            ("0.1.0", n, true),
            ("0.2.0", n, true), // ungated upper bound
        ];
        for &(ver, range, expect) in cases {
            assert_eq!(sat(ver, range), expect, "{ver:?} vs {range:?}");
        }
    }

    #[test]
    fn ordering_rules() {
        let lt = |a: &str, b: &str| {
            compare_semver(&parse_semver(a).unwrap(), &parse_semver(b).unwrap())
        };
        assert_eq!(lt("0.1.0-beta.1", "0.1.0"), Ordering::Less);
        assert_eq!(lt("0.1.0-beta.1", "0.1.0-beta.2"), Ordering::Less);
        assert_eq!(lt("0.1.0", "0.1.0"), Ordering::Equal);
        // numeric prerelease id ranks below alphanumeric, and numerically among themselves
        assert_eq!(lt("1.0.0-alpha.1", "1.0.0-alpha.beta"), Ordering::Less);
        assert_eq!(lt("1.0.0-alpha.2", "1.0.0-alpha.10"), Ordering::Less);
        // fewer prerelease fields ranks lower
        assert_eq!(lt("1.0.0-alpha", "1.0.0-alpha.1"), Ordering::Less);
    }

    #[test]
    fn current_contract_band() {
        // The band SYNC-RUNBOOK.md documents as live (>=0.1.0-beta.2 <0.1.0-beta.3): the client's
        // own contract version must sit inside it, and the neighbours must not.
        let band = ">=0.1.0-beta.2 <0.1.0-beta.3";
        assert!(sat("0.1.0-beta.2", band));
        assert!(!sat("0.1.0-beta.1", band));
        assert!(!sat("0.1.0-beta.3", band));
        assert!(!sat("0.1.0", band));
    }

    #[test]
    fn build_metadata_is_stripped() {
        assert!(sat("0.1.0+build.5", ">=0.1.0 <0.2.0"));
    }

    #[test]
    fn parse_errors_are_returned_not_panics() {
        assert!(version_satisfies("not.a.version", ">=0.1.0").is_err());
        assert!(version_satisfies("0.1.0", ">=not.a.version").is_err());
    }
}
