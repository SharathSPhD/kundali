import Kundali.Vimshottari
import Kundali.Longitude
import Mathlib.Data.Fin.Basic
import Mathlib.Data.Finset.Basic

/-!
Yoga rule predicates mirroring selected rules in `backend/app/engine/yogas.py`.
-/

namespace Kundali

abbrev Sign := Fin 12

structure Chart where
  moonSign : Sign
  jupiterSign : Sign
  jupiterDignity : String := "neutral"
  sunSign : Sign
  mercurySign : Sign
  mercuryCombust : Bool := false
  marsSign : Sign
  venusSign : Sign
  saturnSign : Sign
  moonHouseFromLagna : ℕ
  rahuLongitude : ℚ
  ketuLongitude : ℚ
  classicalLongitude : Lord → ℚ

def kendraHouses : Finset ℕ := {1, 4, 7, 10}

def houseFrom (sign ref : Sign) : ℕ :=
  (sign.val - ref.val + 12) % 12 + 1

def inKendraFrom (sign ref : Sign) : Bool :=
  (houseFrom sign ref) ∈ kendraHouses

/-- Gaja Kesari (BPHS Ch.34): Jupiter in kendra from Moon. -/
def gajaKesari (chart : Chart) : Bool :=
  inKendraFrom chart.jupiterSign chart.moonSign

/-- Budhaditya (BPHS): Sun and Mercury conjunct. -/
def budhaditya (chart : Chart) : Bool :=
  chart.sunSign = chart.mercurySign

/-- Chandra-Mangala (BPHS): Moon and Mars conjunct. -/
def chandraMangala (chart : Chart) : Bool :=
  chart.moonSign = chart.marsSign

def kemadrumaSupportLords : List Lord :=
  [.Mars, .Mercury, .Jupiter, .Venus, .Saturn]

def planetSign (chart : Chart) : Lord → Sign
  | .Mars => chart.marsSign
  | .Mercury => chart.mercurySign
  | .Jupiter => chart.jupiterSign
  | .Venus => chart.venusSign
  | .Saturn => chart.saturnSign
  | .Sun => chart.sunSign
  | .Moon => chart.moonSign
  | _ => chart.moonSign

def kemadrumaRaw (chart : Chart) : Bool :=
  ¬ kemadrumaSupportLords.any fun p =>
    let h := houseFrom (planetSign chart p) chart.moonSign
    h = 1 || h = 2 || h = 12

def kemadrumaCancelled (chart : Chart) : Bool :=
  (kemadrumaSupportLords.any fun p =>
    inKendraFrom (planetSign chart p) chart.moonSign) ||
  decide (chart.moonHouseFromLagna ∈ kendraHouses)

def kemadrumaFinal (chart : Chart) : Bool :=
  kemadrumaRaw chart && !kemadrumaCancelled chart

theorem kemadruma_final_def (chart : Chart) :
    kemadrumaFinal chart = (kemadrumaRaw chart && !kemadrumaCancelled chart) := rfl

theorem kemadruma_cancelled_implies_not (chart : Chart) :
    kemadrumaCancelled chart = true → kemadrumaFinal chart = false := by
  intro hc
  simp [kemadrumaFinal, hc]

theorem kemadruma_present_implies_moon_not_kendra (chart : Chart) :
    kemadrumaFinal chart = true → chart.moonHouseFromLagna ∉ kendraHouses := by
  intro h hk
  have hc : kemadrumaCancelled chart = true := by
    simp [kemadrumaCancelled, hk, decide_eq_true, Bool.or_self]
  have hf : kemadrumaFinal chart = false := by simp [kemadrumaFinal, hc]
  rw [hf] at h
  exact Bool.false_ne_true h

noncomputable def withinArc (lon startLon endLon : ℚ) : Bool :=
  let span := normalize (endLon - startLon)
  let diff := normalize (lon - startLon)
  decide (diff ≤ span)

def classicalPlanets : List Lord :=
  [.Sun, .Moon, .Mars, .Mercury, .Jupiter, .Venus, .Saturn]

noncomputable def kalaSarpa (chart : Chart) : Bool :=
  let insideRK := classicalPlanets.all fun p =>
    withinArc (chart.classicalLongitude p) chart.rahuLongitude chart.ketuLongitude
  let insideKR := classicalPlanets.all fun p =>
    withinArc (chart.classicalLongitude p) chart.ketuLongitude chart.rahuLongitude
  insideRK || insideKR

instance chartDecidable (c : Chart) : Decidable (gajaKesari c) := inferInstance
instance kemadrumaFinalDecidable (c : Chart) : Decidable (kemadrumaFinal c) := inferInstance

def exampleChartGaja : Chart :=
  { moonSign := ⟨0, by decide⟩, jupiterSign := ⟨3, by decide⟩
    sunSign := ⟨5, by decide⟩, mercurySign := ⟨5, by decide⟩, marsSign := ⟨6, by decide⟩
    venusSign := ⟨4, by decide⟩, saturnSign := ⟨7, by decide⟩
    moonHouseFromLagna := 3
    rahuLongitude := 300, ketuLongitude := 120
    classicalLongitude := fun _ => 0 }

theorem gaja_kesari_example : gajaKesari exampleChartGaja = true := by
  simp [gajaKesari, exampleChartGaja, inKendraFrom, houseFrom, kendraHouses]

end Kundali
