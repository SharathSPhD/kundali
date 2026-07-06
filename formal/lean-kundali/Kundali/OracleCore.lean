import Kundali.Longitude
import Kundali.Nakshatra
import Kundali.Vimshottari
import Kundali.Vargas

namespace Kundali

/-- Dasha balance at birth, mirroring `dasha_balance` in `dashas.py`. -/
structure DashaBalance where
  nakshatraIndex : ℕ
  lord : Lord
  balanceYears : ℚ
  deriving Repr

noncomputable def dashaBalance (moonLon : ℚ) : DashaBalance :=
  let lon := normalize moonLon
  let nakNat := (nakshatraIndex lon).val
  let elapsed := (lon - nakNat * nakshatraSpan) / nakshatraSpan
  let lord := nakshatraLord nakNat
  let years := vimshottariYears lord
  { nakshatraIndex := nakNat
    lord := lord
    balanceYears := (years : ℚ) * (1 - elapsed) }

noncomputable def computeVarga (name : String) (lon : ℚ) : Option ℕ :=
  match name with
  | "D1" => some (d1 lon).val
  | "D2" => some (d2 lon).val
  | "D3" => some (d3 lon).val
  | "D9" => some (d9 lon).val
  | "D10" => some (d10 lon).val
  | "D12" => some (d12 lon).val
  | _ => none

noncomputable def antardashaSum (D : ℚ) : ℚ := (antardashaDurations D).sum

end Kundali
