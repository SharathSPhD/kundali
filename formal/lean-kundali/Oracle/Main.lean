import Lean.Data.Json.FromToJson

open Lean

namespace Kundali.Oracle

/-- Arc-minutes (1/60°). Full circle = 21600. Computable mirror of Python rules. -/
abbrev ArcMin := Nat
def fullCircleMin : ArcMin := 21600

def normalizeMin (x : Int) : ArcMin :=
  let m := x % (fullCircleMin : Int)
  Int.toNat (if m < 0 then m + fullCircleMin else m)

def signSpanMin : ArcMin := 1800

def signDegMin (lonMin : ArcMin) : Nat × ArcMin :=
  let sign := lonMin / signSpanMin
  let deg := lonMin % signSpanMin
  (sign % 12, deg)

def partMin (deg : ArcMin) (span : ArcMin) (nparts : Nat) : Nat :=
  min (deg / span) (nparts - 1)

def oddSign (s : Nat) : Bool := s % 2 = 0

def d1Min (lon : ArcMin) : Nat := (signDegMin lon).1

def d2Min (lon : ArcMin) : Nat :=
  let (sign, deg) := signDegMin lon
  let firstHalf := deg < 900
  if oddSign sign then (if firstHalf then 4 else 3) else (if firstHalf then 3 else 4)

def d3Min (lon : ArcMin) : Nat :=
  let (sign, deg) := signDegMin lon
  let p := partMin deg 600 3
  (sign + p * 4) % 12

def d9Min (lon : ArcMin) : Nat :=
  let (sign, deg) := signDegMin lon
  let p := partMin deg 200 9
  let start := match sign % 3 with | 0 => sign | 1 => (sign + 8) % 12 | _ => (sign + 4) % 12
  (start + p) % 12

def d10Min (lon : ArcMin) : Nat :=
  let (sign, deg) := signDegMin lon
  let p := partMin deg 180 10
  let start := if oddSign sign then sign else (sign + 8) % 12
  (start + p) % 12

def d12Min (lon : ArcMin) : Nat :=
  let (sign, deg) := signDegMin lon
  let p := partMin deg 150 12
  (sign + p) % 12

def computeVargaMin (name : String) (lon : ArcMin) : Option Nat :=
  match name with
  | "D1" => some (d1Min lon)
  | "D2" => some (d2Min lon)
  | "D3" => some (d3Min lon)
  | "D9" => some (d9Min lon)
  | "D10" => some (d10Min lon)
  | "D12" => some (d12Min lon)
  | _ => none

def nakshatraSpanMin : ArcMin := 800
def padaSpanMin : ArcMin := 200

def nakshatraIndexMin (lon : ArcMin) : Nat := (lon / nakshatraSpanMin) % 27
def padaIndexMin (lon : ArcMin) : Nat := (lon / padaSpanMin) % 4

inductive Lord where
  | Ketu | Venus | Sun | Moon | Mars | Rahu | Jupiter | Saturn | Mercury
  deriving Repr, DecidableEq

def vimshottariOrder : List Lord :=
  [.Ketu, .Venus, .Sun, .Moon, .Mars, .Rahu, .Jupiter, .Saturn, .Mercury]

def vimshottariYears : Lord → Nat
  | .Ketu => 7 | .Venus => 20 | .Sun => 6 | .Moon => 10 | .Mars => 7
  | .Rahu => 18 | .Jupiter => 16 | .Saturn => 19 | .Mercury => 17

def lordToString : Lord → String
  | .Ketu => "Ketu" | .Venus => "Venus" | .Sun => "Sun" | .Moon => "Moon"
  | .Mars => "Mars" | .Rahu => "Rahu" | .Jupiter => "Jupiter"
  | .Saturn => "Saturn" | .Mercury => "Mercury"

def nakshatraLord (nak : Nat) : Lord :=
  match vimshottariOrder[nak % 9]? with
  | some l => l
  | none => .Ketu

def floatToArcMin (f : Float) : ArcMin :=
  normalizeMin (Int.ofNat (f * 60000 |>.round.toUInt64.toNat))

def trimLeft (s : String) : String :=
  (s.dropWhile fun c => c == ' ' || c == '\t').toString

def extractNat (key : String) (text : String) : Option Nat :=
  let needle := s!"\"{key}\":"
  match text.splitOn needle with
  | _ :: rest =>
    let tail := trimLeft (rest.head!)
    let num := (tail.takeWhile Char.isDigit).toString
    String.toNat? num
  | _ => none

def microdegToArcMin (micro : Nat) : ArcMin :=
  (micro * 60) / 1000000

def extractLabel (text : String) : String :=
  match text.splitOn "\"label\":" with
  | _ :: rest =>
    let t := trimLeft (rest.head!)
    if t.startsWith "\"" then
      ((t.drop 1).takeWhile fun c => c ≠ '"').toString
    else "case"
  | _ => "case"

structure Input where
  label : String
  moon_longitude_micro : Nat
  lonMin : ArcMin
  mahadasha_duration_micro : Nat
  vargas : List String

def parseInputFile (text : String) : Option Input := do
  let micro ← extractNat "moon_longitude_microdeg" text
  let durMicro := extractNat "mahadasha_duration_micro" text |>.getD 120000000
  let label := extractLabel text
  return { label, moon_longitude_micro := micro, lonMin := microdegToArcMin micro,
           mahadasha_duration_micro := durMicro,
           vargas := ["D1", "D2", "D3", "D9", "D10", "D12"] }

def dashaBalanceFromMicro (micro : Nat) : Lord × Float :=
  let deg := (micro.toFloat) / 1000000.0
  let lon := deg - Float.floor (deg / 360.0) * 360.0
  let nakFloat := lon / (360.0 / 27.0)
  let nak := Int.toNat (Float.floor nakFloat).toUInt64.toNat % 27
  let elapsed := nakFloat - Float.floor nakFloat
  let lord := nakshatraLord nak
  let years := (vimshottariYears lord).toFloat
  (lord, years * (1.0 - elapsed))

def antardashaSumMin (durMicro : Nat) : Float :=
  let dur := (durMicro.toFloat) / 1000000.0
  let total := vimshottariOrder.foldl (fun acc l => acc + vimshottariYears l) 0
  vimshottariOrder.foldl
    (fun acc l => acc + dur * (vimshottariYears l).toFloat / total.toFloat) 0.0

def computeJson (inp : Input) : Json :=
  let lonMin := inp.lonMin
  let (lord, bal) := dashaBalanceFromMicro inp.moon_longitude_micro
  let vargObj := Json.mkObj (inp.vargas.filterMap fun name =>
    match computeVargaMin name lonMin with
    | some s => some (name, toJson s)
    | none => none)
  Json.mkObj [
    ("label", toJson inp.label),
    ("nakshatra_index", toJson (nakshatraIndexMin lonMin)),
    ("pada_index", toJson (padaIndexMin lonMin)),
    ("vimshottari_first_lord", toJson (lordToString lord)),
    ("vimshottari_balance_years", toJson bal),
    ("antardasha_duration_sum", toJson (antardashaSumMin inp.mahadasha_duration_micro)),
    ("vargas", vargObj)
  ]

def run (args : List String) : IO UInt32 := do
  let path := args.getD 0 "formal/schemas/chart_oracle_v1.example.json"
  let contents ← IO.FS.readFile path
  match parseInputFile contents with
  | none =>
    IO.eprintln "Invalid input JSON (need moon_longitude_microdeg field)"
    return 1
  | some inp =>
    IO.println (computeJson inp).compress
    return 0

end Kundali.Oracle

def main (args : List String) : IO UInt32 :=
  Kundali.Oracle.run args
