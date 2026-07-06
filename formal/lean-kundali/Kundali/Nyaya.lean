/-!
Nyaya (Indian logic) syllogism scaffold — five-member argument form.

This module verifies argument *FORM* only (vyāpti stated, dṛṣṭānta present, no hetvābhāsa).
It does **not** and **cannot** verify astrological or worldly truth of any conclusion.

Must stay in sync with `backend/app/oracle/nyaya_bridge.py`.
-/

namespace Kundali.Nyaya

/-- Classical five-member syllogism (Nyaya pramana / pañcāvayava). -/
structure Syllogism where
  pratijna : String      -- thesis (proposition)
  hetu : String          -- reason (middle term)
  udaharana : String     -- example / vyapti witness (dṛṣṭānta)
  upanaya : String       -- application
  nigamana : String      -- conclusion
  vyapti_stated : Bool   -- general rule (major premise) explicitly present
  drstanta_present : Bool
  hetvabhasa : Option String := none  -- named fallacy if detected
  deriving Repr, DecidableEq

def nonempty (s : String) : Bool := !s.isEmpty

def hasAllMembers (s : Syllogism) : Bool :=
  nonempty s.pratijna && nonempty s.hetu && nonempty s.upanaya && nonempty s.nigamana

/-- Decidable well-formedness: all members present, vyāpti & dṛṣṭānta flags set, no hetvābhāsa. -/
def wellFormed (s : Syllogism) : Bool :=
  hasAllMembers s && s.vyapti_stated && s.drstanta_present && s.hetvabhasa.isNone

def exampleValid : Syllogism :=
  { pratijna := "This hill has fire"
    hetu := "Because it has smoke"
    udaharana := "A kitchen has smoke and fire"
    upanaya := "This hill has smoke like the kitchen"
    nigamana := "Therefore this hill has fire"
    vyapti_stated := true
    drstanta_present := true }

def exampleMissingVyapti : Syllogism :=
  { pratijna := "This hill has fire"
    hetu := "Because it has smoke"
    udaharana := "Kitchen example"
    upanaya := "This hill has smoke"
    nigamana := "Therefore fire"
    vyapti_stated := false
    drstanta_present := true }

def exampleWithFallacy : Syllogism :=
  { pratijna := "Sound is eternal"
    hetu := "Because it is audible"
    udaharana := "Sound is audible"
    upanaya := "Sound is audible"
    nigamana := "Sound is eternal"
    vyapti_stated := true
    drstanta_present := true
    hetvabhasa := some "savyabhicara" }

theorem nyaya_valid_example : wellFormed exampleValid := by native_decide
theorem nyaya_missing_vyapti : ¬ wellFormed exampleMissingVyapti := by native_decide
theorem nyaya_with_fallacy : ¬ wellFormed exampleWithFallacy := by native_decide

end Kundali.Nyaya
