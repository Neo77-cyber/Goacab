import { useEffect, useState, type ChangeEvent, type FormEvent } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import {
  getBankOptions,
  registerDriver,
  registerRider,
  requestCode,
  type BankOption,
  type DriverRegisterFields,
  type DriverRegisterFiles,
} from "../api/auth";
import { ApiError } from "../api/http";
import { useAuth } from "../auth/AuthContext";
import { resumePendingBookingIfAny } from "../booking/pendingBooking";
import { useAutoDismiss } from "../hooks/useAutoDismiss";
import { getCurrentPosition } from "../lib/geolocation";

type Role = "rider" | "driver";
type RiderStep = "role" | "name" | "phone" | "location" | "verify";
type DriverStep =
  | "vehicle"
  | "name"
  | "dob"
  | "phone"
  | "selfie"
  | "license"
  | "nin"
  | "vehiclePhoto"
  | "vehicleDetails"
  | "bank"
  | "location"
  | "verify";

// Mirrors the server's phonenumbers-based check closely enough to catch a
// bad number immediately, before the user fills out the rest of a
// multi-step form only to have it rejected at the very last step. Nigerian
// mobile subscriber numbers are exactly 10 digits starting with 7/8/9 —
// this input's "+234" prefix is already shown separately, so the field
// itself should hold just that 10-digit number (an optional leading 0, as
// people habitually type, is tolerated and stripped).
function isValidNigerianLocalNumber(raw: string): boolean {
  const digits = raw.replace(/\D/g, "");
  const local = digits.startsWith("0") ? digits.slice(1) : digits;
  return /^[789]\d{9}$/.test(local);
}

const FILE_FIELDS: (keyof DriverRegisterFiles)[] = [
  "drivers_license",
  "passport_photo",
  "nin_slip_photo",
  "vehicle_picture",
];

const FILE_LABELS: Record<keyof DriverRegisterFiles, string> = {
  drivers_license: "Driver's license",
  passport_photo: "Selfie",
  nin_slip_photo: "NIN slip photo",
  vehicle_picture: "Vehicle picture",
};

export default function Signup() {
  const { setSession } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const navState = location.state as { email?: string; verifiedToken?: string } | null;
  const prefilledEmail = navState?.email ?? "";
  const verifiedToken = navState?.verifiedToken;
  // A referral link (see Referrals.tsx's share text) looks like
  // /signup?ref=ABC123 — prefilled here but still editable/removable, same
  // as every other field in this form.
  const prefilledReferralCode = new URLSearchParams(location.search).get("ref") ?? "";

  const [role, setRole] = useState<Role | null>(null);
  const [riderStep, setRiderStep] = useState<RiderStep>("role");
  const [driverStep, setDriverStep] = useState<DriverStep>("vehicle");
  const [codeSent, setCodeSent] = useState(false);
  const [code, setCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [driverPending, setDriverPending] = useState(false);

  useAutoDismiss(error, () => setError(null));

  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState(prefilledEmail);
  const [phoneNumber, setPhoneNumber] = useState("");
  const [phoneLocal, setPhoneLocal] = useState("");
  const [address] = useState("");
  const [referralCode, setReferralCode] = useState(prefilledReferralCode.toUpperCase());
  const [locationStatus, setLocationStatus] = useState<"idle" | "requesting" | "granted" | "denied">("idle");

  const [dateOfBirth, setDateOfBirth] = useState("");
  const [nin, setNin] = useState("");
  const [vehicleType, setVehicleType] = useState<"Bike" | "Bicycle">("Bike");
  const [vehicleModel, setVehicleModel] = useState("");
  const [vehicleBrand, setVehicleBrand] = useState("");
  const [vehicleColor, setVehicleColor] = useState("");
  const [productionYear, setProductionYear] = useState("");
  const [licensePlate, setLicensePlate] = useState("");
  const [bankName, setBankName] = useState("");
  const [bankCode, setBankCode] = useState("");
  const [bankOptions, setBankOptions] = useState<BankOption[]>([]);
  const [accountNumber, setAccountNumber] = useState("");
  const [accountHolderName, setAccountHolderName] = useState("");
  const [latitude, setLatitude] = useState("");
  const [longitude, setLongitude] = useState("");
  const [files, setFiles] = useState<Partial<Record<keyof DriverRegisterFiles, File>>>({});
  const [agreedToTerms, setAgreedToTerms] = useState(false);

  useEffect(() => {
    getBankOptions().then(setBankOptions);
  }, []);

  function useMyLocation() {
    setLocationStatus("requesting");
    getCurrentPosition(
      (coords) => {
        setLatitude(String(coords.latitude));
        setLongitude(String(coords.longitude));
        setLocationStatus("granted");
      },
      () => {
        setLocationStatus("denied");
      },
    );
  }

  function handleFileChange(field: keyof DriverRegisterFiles) {
    return (e: ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      setFiles((prev) => ({ ...prev, [field]: file }));
    };
  }

  async function handleSendCode() {
    setError(null);
    if (!email.trim()) {
      setError("Enter your email first.");
      return;
    }
    setLoading(true);
    try {
      await requestCode(email.trim());
      setCodeSent(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not send code.");
    } finally {
      setLoading(false);
    }
  }

  function selectRole(r: Role) {
    setError(null);
    setRole(r);
    if (r === "rider") setRiderStep("name");
    if (r === "driver") setDriverStep("vehicle");
  }

  function goToPhoneStep() {
    if (!fullName.trim()) {
      setError("Enter your name to continue.");
      return;
    }
    setError(null);
    setRiderStep("phone");
  }

  function goToLocationStep() {
    const digits = phoneLocal.replace(/\D/g, "");
    if (!digits) {
      setError("Enter your phone number to continue.");
      return;
    }
    if (!isValidNigerianLocalNumber(digits)) {
      setError("Enter a valid Nigerian phone number, e.g. 8012345678 or 08012345678.");
      return;
    }
    const withoutLeadingZero = digits.startsWith("0") ? digits.slice(1) : digits;
    setPhoneNumber(`+234${withoutLeadingZero}`);
    setError(null);
    setRiderStep("location");
  }

  function goToVerifyStep() {
    setError(null);
    setRiderStep("verify");
  }

  function goToDriverNameStep() {
    setError(null);
    setDriverStep("name");
  }

  function goToDriverDobStep() {
    if (!fullName.trim()) {
      setError("Enter your name to continue.");
      return;
    }
    setError(null);
    setDriverStep("dob");
  }

  function goToDriverPhoneStep() {
    if (!dateOfBirth) {
      setError("Enter your date of birth to continue.");
      return;
    }
    setError(null);
    setDriverStep("phone");
  }

  function goToDriverSelfieStep() {
    const digits = phoneLocal.replace(/\D/g, "");
    if (!digits) {
      setError("Enter your phone number to continue.");
      return;
    }
    if (!isValidNigerianLocalNumber(digits)) {
      setError("Enter a valid Nigerian phone number, e.g. 8012345678 or 08012345678.");
      return;
    }
    const withoutLeadingZero = digits.startsWith("0") ? digits.slice(1) : digits;
    setPhoneNumber(`+234${withoutLeadingZero}`);
    setError(null);
    setDriverStep("selfie");
  }

  function goToDriverLicenseStep() {
    if (!files.passport_photo) {
      setError("Upload a selfie to continue.");
      return;
    }
    setError(null);
    setDriverStep("license");
  }

  function goToDriverNinStep() {
    if (!files.drivers_license) {
      setError("Upload your driver's license to continue.");
      return;
    }
    setError(null);
    setDriverStep("nin");
  }

  function goToDriverVehiclePhotoStep() {
    if (!nin.trim()) {
      setError("Enter your NIN to continue.");
      return;
    }
    if (!files.nin_slip_photo) {
      setError("Upload a photo of your NIN slip to continue.");
      return;
    }
    setError(null);
    setDriverStep("vehiclePhoto");
  }

  function goToDriverVehicleDetailsStep() {
    if (!files.vehicle_picture) {
      setError("Upload a picture of your vehicle to continue.");
      return;
    }
    setError(null);
    setDriverStep("vehicleDetails");
  }

  function goToDriverBankStep() {
    if (!vehicleColor.trim()) {
      setError("Enter your vehicle's color to continue.");
      return;
    }
    if (vehicleType === "Bike") {
      const missing = [];
      if (!vehicleBrand.trim()) missing.push("vehicle brand");
      if (!vehicleModel.trim()) missing.push("vehicle model");
      if (!licensePlate.trim()) missing.push("plate number");
      if (!productionYear.trim()) missing.push("production year");
      if (missing.length > 0) {
        setError(`Enter your ${missing.join(", ")} to continue.`);
        return;
      }
    }
    setError(null);
    setDriverStep("bank");
  }

  function goToDriverLocationStep() {
    if (!bankCode || !accountNumber.trim() || !accountHolderName.trim()) {
      setError("Fill in your bank details to continue.");
      return;
    }
    setError(null);
    setDriverStep("location");
  }

  function goToDriverVerifyStep() {
    setError(null);
    setDriverStep("verify");
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      if (role === "rider") {
        const tokens = await registerRider({
          full_name: fullName,
          phone_number: phoneNumber,
          email: email.trim(),
          address: address || undefined,
          ...(verifiedToken ? { verified_token: verifiedToken } : { code: code.trim() }),
          latitude: latitude ? Number(latitude) : undefined,
          longitude: longitude ? Number(longitude) : undefined,
          referral_code: referralCode.trim() || undefined,
        });
        setSession(tokens);
        const resume = await resumePendingBookingIfAny(tokens.access, "rider");
        navigate("/rider", {
          state: resume.resumed
            ? { bookedRideId: resume.rideId }
            : resume.error
              ? { bookingError: resume.error }
              : undefined,
        });
        return;
      }

      const missing = FILE_FIELDS.filter((field) => !files[field]);
      if (missing.length > 0) {
        setError(`Missing files: ${missing.map((f) => FILE_LABELS[f]).join(", ")}`);
        setLoading(false);
        return;
      }

      if (vehicleType === "Bike" && !licensePlate.trim()) {
        setError("License plate is required for a Bike.");
        setLoading(false);
        return;
      }

      if (!latitude || !longitude) {
        setError("Set your current location using the button below.");
        setLoading(false);
        return;
      }

      const fields: DriverRegisterFields = {
        full_name: fullName,
        email: email.trim(),
        phone_number: phoneNumber,
        ...(verifiedToken ? { verified_token: verifiedToken } : { code: code.trim() }),
        date_of_birth: dateOfBirth,
        national_identification_number: nin,
        vehicle_type: vehicleType,
        vehicle_color: vehicleColor,
        vehicle_brand: vehicleType === "Bike" ? vehicleBrand : undefined,
        vehicle_model: vehicleType === "Bike" ? vehicleModel : undefined,
        license_plate: vehicleType === "Bike" ? licensePlate : undefined,
        production_year: vehicleType === "Bike" && productionYear ? Number(productionYear) : undefined,
        bank_name: bankName,
        bank_code: bankCode,
        account_number: accountNumber,
        account_holder_name: accountHolderName,
        latitude: Number(latitude),
        longitude: Number(longitude),
      };
      await registerDriver(fields, files as DriverRegisterFiles);
      setDriverPending(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Registration failed.");
    } finally {
      setLoading(false);
    }
  }

  if (driverPending) {
    return (
      <div className="relative w-full max-w-[480px] mx-auto min-h-dvh bg-[#20241f] flex flex-col items-center justify-center text-slate-100 px-8 gap-4 text-center">
        <h1 className="text-white text-2xl font-extrabold">Registration submitted</h1>
        <p className="text-slate-300/80 text-sm max-w-[320px]">
          Your driver account is awaiting approval. This usually takes within 30 minutes.
          You'll be able to log in with your email once approved.
        </p>
        <Link to="/login" className="text-[#1be451] font-semibold text-sm">Back to login</Link>
      </div>
    );
  }

  // ── Role picker (step 1, shared entry point) ──────────────────────────────
  if (role === null) {
    return (
      <div className="relative w-full max-w-[480px] mx-auto min-h-dvh bg-[#20241f] flex flex-col items-center justify-center text-slate-100 px-8 gap-4">
        <h1 className="text-white text-2xl font-extrabold mb-2">How will you use GoCab?</h1>
        <button
          onClick={() => selectRole("rider")}
          className="w-full max-w-[320px] py-4 rounded-full bg-[#1be451] text-neutral-900 font-bold text-lg shadow-md"
        >
          I am a passenger
        </button>
        <button
          onClick={() => selectRole("driver")}
          className="w-full max-w-[320px] py-4 rounded-full bg-white/10 border border-white/20 text-white font-bold text-lg"
        >
          I am a rider
        </button>
       
      </div>
    );
  }

  // ── Rider wizard (steps 2-5) ───────────────────────────────────────────────
  if (role === "rider") {
    return (
      <div className="relative w-full max-w-[480px] mx-auto min-h-dvh bg-[#20241f] flex flex-col items-center justify-center text-slate-100 px-8 gap-4">
        <button
          onClick={() => {
            setError(null);
            if (riderStep === "name") {
              setRole(null);
            } else if (riderStep === "phone") {
              setRiderStep("name");
            } else if (riderStep === "location") {
              setRiderStep("phone");
            } else if (riderStep === "verify") {
              setRiderStep("location");
            }
          }}
          className="self-start text-slate-400 text-sm"
        >
          ← Back
        </button>

        {riderStep === "name" && (
          <div className="w-full max-w-[320px] flex flex-col gap-4">
            <h1 className="text-white text-2xl font-extrabold">What's your name?</h1>
            <input
              autoFocus
              value={fullName}
              maxLength={255}
            onChange={(e) => setFullName(e.target.value)}
              placeholder="Full name"
              className="w-full rounded-full px-4 py-3 bg-white/10 border border-white/20 text-white placeholder:text-slate-400"
            />
            <button onClick={goToPhoneStep} className="w-full py-3 rounded-full bg-[#1be451] text-neutral-900 font-bold">
              Next
            </button>
          </div>
        )}

        {riderStep === "phone" && (
          <div className="w-full max-w-[320px] flex flex-col gap-4">
            <h1 className="text-white text-2xl font-extrabold">What's your phone number?</h1>
            <div className="flex items-center rounded-full bg-white/10 border border-white/20 overflow-hidden">
              <span className="px-4 py-3 text-slate-300 font-semibold border-r border-white/20">+234</span>
              <input
                autoFocus
                inputMode="numeric"
                value={phoneLocal}
                onChange={(e) => setPhoneLocal(e.target.value.replace(/\D/g, "").slice(0, 11))}
                placeholder="8012345678"
                className="flex-1 px-4 py-3 bg-transparent text-white placeholder:text-slate-400 outline-none"
              />
            </div>
            <button onClick={goToLocationStep} className="w-full py-3 rounded-full bg-[#1be451] text-neutral-900 font-bold">
              Next
            </button>
          </div>
        )}

        {riderStep === "location" && (
          <div className="w-full max-w-[320px] flex flex-col gap-4">
            <h1 className="text-white text-2xl font-extrabold">Enable location</h1>
            <p className="text-slate-300/80 text-sm">
              GoCab uses your location to match you with nearby riders and track your trips.
            </p>
            <button
              onClick={useMyLocation}
              className="w-full py-3 rounded-full bg-white/10 border border-white/20 text-white font-semibold"
            >
              {locationStatus === "requesting"
                ? "Requesting…"
                : locationStatus === "granted"
                  ? "Location enabled "
                  : locationStatus === "denied"
                    ? "Couldn't get location, try again"
                    : "Enable location"}
            </button>
            <button onClick={goToVerifyStep} className="w-full py-3 rounded-full bg-[#1be451] text-neutral-900 font-bold">
              {locationStatus === "granted" ? "Next" : "Skip for now"}
            </button>
          </div>
        )}

        {riderStep === "verify" && (
          <form
            onSubmit={handleSubmit}
            className="w-full max-w-[320px] flex flex-col gap-4"
          >
            {verifiedToken ? (
              <>
                <h1 className="text-white text-2xl font-extrabold">Confirm your email</h1>
                <p className="text-slate-300/80 text-sm">
                  We already confirmed <span className="text-white font-semibold">{email}</span>, no need to verify it again.
                </p>
              </>
            ) : (
              <>
                <h1 className="text-white text-2xl font-extrabold">Verify your email</h1>
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="Email address"
                  className="w-full rounded-full px-4 py-3 bg-white/10 border border-white/20 text-white placeholder:text-slate-400"
                />
                <button
                  type="button"
                  onClick={handleSendCode}
                  disabled={loading}
                  className="w-full py-3 rounded-full bg-white/10 border border-white/20 text-white font-semibold"
                >
                  {loading ? "Sending…" : codeSent ? "Resend code" : "Send code"}
                </button>

                {codeSent && (
                  <input
                    required
                    inputMode="numeric"
                    maxLength={6}
                    value={code}
                    onChange={(e) => setCode(e.target.value)}
                    placeholder="6-digit code"
                    className="w-full rounded-full px-4 py-3 bg-white/10 border border-white/20 text-white placeholder:text-slate-400"
                  />
                )}
              </>
            )}

            <input
              value={referralCode}
              onChange={(e) => setReferralCode(e.target.value.toUpperCase())}
              placeholder="Referral code (optional)"
              className="w-full rounded-full px-4 py-3 bg-white/10 border border-white/20 text-white placeholder:text-slate-400"
            />

            <label className="flex items-start gap-2 text-slate-300 text-xs">
              <input
                type="checkbox"
                required
                checked={agreedToTerms}
                onChange={(e) => setAgreedToTerms(e.target.checked)}
                className="mt-0.5 shrink-0"
              />
              <span>
                I agree to the <a href="/terms" target="_blank" rel="noopener noreferrer" className="underline text-[#1be451]">Terms &amp; Conditions</a> and{" "}
                <a href="/privacy" target="_blank" rel="noopener noreferrer" className="underline text-[#1be451]">Privacy Policy</a>
              </span>
            </label>

            <button
              type="submit"
              disabled={loading || (!verifiedToken && !codeSent) || !agreedToTerms}
              className="w-full py-3 rounded-full bg-[#1be451] text-neutral-900 font-bold disabled:opacity-50"
            >
              {loading ? "Creating account…" : "Create account"}
            </button>

            {error && <p className="text-red-400 text-sm">{error}</p>}
          </form>
        )}

        {error && riderStep !== "verify" && <p className="text-red-400 text-sm">{error}</p>}
      </div>
    );
  }

  // ── Driver wizard ──────────────────────────────────────────────────────────
  const inputClass =
    "w-full rounded-full px-4 py-3 bg-white/10 border border-white/20 text-white placeholder:text-slate-400";
  const nextButtonClass = "w-full py-3 rounded-full bg-[#1be451] text-neutral-900 font-bold";
  const fileChosenClass = "text-[#1be451] text-xs";

  function driverBack() {
    setError(null);
    const prevStep: Partial<Record<DriverStep, DriverStep | null>> = {
      vehicle: null,
      name: "vehicle",
      dob: "name",
      phone: "dob",
      selfie: "phone",
      license: "selfie",
      nin: "license",
      vehiclePhoto: "nin",
      vehicleDetails: "vehiclePhoto",
      bank: "vehicleDetails",
      location: "bank",
      verify: "location",
    };
    const prev = prevStep[driverStep];
    if (prev === null || prev === undefined) {
      setRole(null);
    } else {
      setDriverStep(prev);
    }
  }

  return (
    <div className="relative w-full max-w-[480px] mx-auto min-h-dvh bg-[#20241f] flex flex-col items-center justify-center text-slate-100 px-8 gap-4">
      <button onClick={driverBack} className="self-start text-slate-400 text-sm">
        ← Back
      </button>

      {driverStep === "vehicle" && (
        <div className="w-full max-w-[320px] flex flex-col gap-4">
          <h1 className="text-white text-2xl font-extrabold">Bike or bicycle?</h1>
          <button
            onClick={() => {
              setVehicleType("Bike");
              goToDriverNameStep();
            }}
            className="w-full py-4 rounded-full bg-[#1be451] text-neutral-900 font-bold text-lg shadow-md"
          >
            Bike
          </button>
          <button
            onClick={() => {
              setVehicleType("Bicycle");
              goToDriverNameStep();
            }}
            className="w-full py-4 rounded-full bg-white/10 border border-white/20 text-white font-bold text-lg"
          >
            Bicycle
          </button>
        </div>
      )}

      {driverStep === "name" && (
        <div className="w-full max-w-[320px] flex flex-col gap-4">
          <h1 className="text-white text-2xl font-extrabold">What's your name?</h1>
          <input
            autoFocus
            value={fullName}
            maxLength={255}
            onChange={(e) => setFullName(e.target.value)}
            placeholder="Full name"
            className={inputClass}
          />
          <button onClick={goToDriverDobStep} className={nextButtonClass}>Next</button>
        </div>
      )}

      {driverStep === "dob" && (
        <div className="w-full max-w-[320px] flex flex-col gap-4">
          <h1 className="text-white text-2xl font-extrabold">Date of birth</h1>
          <input
            autoFocus
            type="date"
            value={dateOfBirth}
            onChange={(e) => setDateOfBirth(e.target.value)}
            className={inputClass}
          />
          <button onClick={goToDriverPhoneStep} className={nextButtonClass}>Next</button>
        </div>
      )}

      {driverStep === "phone" && (
        <div className="w-full max-w-[320px] flex flex-col gap-4">
          <h1 className="text-white text-2xl font-extrabold">What's your phone number?</h1>
          <div className="flex items-center rounded-full bg-white/10 border border-white/20 overflow-hidden">
            <span className="px-4 py-3 text-slate-300 font-semibold border-r border-white/20">+234</span>
            <input
              autoFocus
              inputMode="numeric"
              value={phoneLocal}
              onChange={(e) => setPhoneLocal(e.target.value.replace(/\D/g, "").slice(0, 11))}
              placeholder="8012345678"
              className="flex-1 px-4 py-3 bg-transparent text-white placeholder:text-slate-400 outline-none"
            />
          </div>
          <button onClick={goToDriverSelfieStep} className={nextButtonClass}>Next</button>
        </div>
      )}

      {driverStep === "selfie" && (
        <div className="w-full max-w-[320px] flex flex-col gap-4">
          <h1 className="text-white text-2xl font-extrabold">Take a selfie</h1>
          <p className="text-slate-300/80 text-sm">A clear photo of your face, for identity verification.</p>
          <input type="file" accept="image/*" capture="user" onChange={handleFileChange("passport_photo")} className="text-white text-sm" />
          {files.passport_photo && <p className={fileChosenClass}>Selected: {files.passport_photo.name}</p>}
          <button onClick={goToDriverLicenseStep} className={nextButtonClass}>Next</button>
        </div>
      )}

      {driverStep === "license" && (
        <div className="w-full max-w-[320px] flex flex-col gap-4">
          <h1 className="text-white text-2xl font-extrabold">Driver's license</h1>
          <p className="text-slate-300/80 text-sm">Upload a photo of your driver's license.</p>
          <input type="file" accept="image/*,.pdf" onChange={handleFileChange("drivers_license")} className="text-white text-sm" />
          {files.drivers_license && <p className={fileChosenClass}>Selected: {files.drivers_license.name}</p>}
          <button onClick={goToDriverNinStep} className={nextButtonClass}>Next</button>
        </div>
      )}

      {driverStep === "nin" && (
        <div className="w-full max-w-[320px] flex flex-col gap-4">
          <h1 className="text-white text-2xl font-extrabold">Your NIN</h1>
          <input
            autoFocus
            value={nin}
            maxLength={100}
            onChange={(e) => setNin(e.target.value)}
            placeholder="NIN number"
            className={inputClass}
          />
          <p className="text-slate-300/80 text-sm">Upload a photo of your NIN slip.</p>
          <input type="file" accept="image/*,.pdf" onChange={handleFileChange("nin_slip_photo")} className="text-white text-sm" />
          {files.nin_slip_photo && <p className={fileChosenClass}>Selected: {files.nin_slip_photo.name}</p>}
          <button onClick={goToDriverVehiclePhotoStep} className={nextButtonClass}>Next</button>
        </div>
      )}

      {driverStep === "vehiclePhoto" && (
        <div className="w-full max-w-[320px] flex flex-col gap-4">
          <h1 className="text-white text-2xl font-extrabold">Your {vehicleType.toLowerCase()}</h1>
          <p className="text-slate-300/80 text-sm">Upload a clear photo of your {vehicleType.toLowerCase()}.</p>
          <input type="file" accept="image/*" onChange={handleFileChange("vehicle_picture")} className="text-white text-sm" />
          {files.vehicle_picture && <p className={fileChosenClass}>Selected: {files.vehicle_picture.name}</p>}
          <button onClick={goToDriverVehicleDetailsStep} className={nextButtonClass}>Next</button>
        </div>
      )}

      {driverStep === "vehicleDetails" && (
        <div className="w-full max-w-[320px] flex flex-col gap-4">
          <h1 className="text-white text-2xl font-extrabold">{vehicleType} details</h1>
          <input
            autoFocus
            value={vehicleColor}
            maxLength={50}
            onChange={(e) => setVehicleColor(e.target.value)}
            placeholder="Color"
            className={inputClass}
          />
          {vehicleType === "Bike" && (
            <>
              <input
                value={vehicleBrand}
                maxLength={100}
            onChange={(e) => setVehicleBrand(e.target.value)}
                placeholder="Brand (e.g. Honda)"
                className={inputClass}
              />
              <input
                value={vehicleModel}
                maxLength={100}
            onChange={(e) => setVehicleModel(e.target.value)}
                placeholder="Model (e.g. CG125)"
                className={inputClass}
              />
              <input
                value={licensePlate}
                maxLength={100}
            onChange={(e) => setLicensePlate(e.target.value)}
                placeholder="Plate number"
                className={inputClass}
              />
              <input
                inputMode="numeric"
                maxLength={4}
                value={productionYear}
                onChange={(e) => setProductionYear(e.target.value.replace(/\D/g, ""))}
                placeholder="Production year"
                className={inputClass}
              />
            </>
          )}
          <button onClick={goToDriverBankStep} className={nextButtonClass}>Next</button>
        </div>
      )}

      {driverStep === "bank" && (
        <div className="w-full max-w-[320px] flex flex-col gap-4">
          <h1 className="text-white text-2xl font-extrabold">Bank details</h1>
          <p className="text-slate-300/80 text-sm">So we know where to send your payouts.</p>
          <select
            autoFocus
            value={bankCode}
            onChange={(e) => {
              const selected = bankOptions.find((b) => b.code === e.target.value);
              setBankCode(e.target.value);
              setBankName(selected?.name ?? "");
            }}
            className={`${inputClass} ${bankCode ? "" : "text-slate-400"}`}
          >
            <option value="" disabled>
              {bankOptions.length === 0 ? "Loading banks…" : "Select your bank"}
            </option>
            {bankOptions.map((b) => (
              <option key={b.code} value={b.code} className="text-black">
                {b.name}
              </option>
            ))}
          </select>
          <input
            inputMode="numeric"
            maxLength={10}
            value={accountNumber}
            onChange={(e) => setAccountNumber(e.target.value.replace(/\D/g, ""))}
            placeholder="Account number"
            className={inputClass}
          />
          <input
            value={accountHolderName}
            maxLength={255}
            onChange={(e) => setAccountHolderName(e.target.value)}
            placeholder="Account holder name"
            className={inputClass}
          />
          <button onClick={goToDriverLocationStep} className={nextButtonClass}>Next</button>
        </div>
      )}

      {driverStep === "location" && (
        <div className="w-full max-w-[320px] flex flex-col gap-4">
          <h1 className="text-white text-2xl font-extrabold">Enable location</h1>
          <p className="text-slate-300/80 text-sm">
            GoCab uses your location to match you with nearby ride requests.
          </p>
          <button
            onClick={useMyLocation}
            className="w-full py-3 rounded-full bg-white/10 border border-white/20 text-white font-semibold"
          >
            {locationStatus === "requesting"
              ? "Requesting…"
              : locationStatus === "granted"
                ? "Location enabled"
                : locationStatus === "denied"
                  ? "Couldn't get location, try again"
                  : "Enable location"}
          </button>
          <button
            onClick={() => {
              if (!latitude || !longitude) {
                setError("Enable location to continue.");
                return;
              }
              goToDriverVerifyStep();
            }}
            className={nextButtonClass}
          >
            Next
          </button>
        </div>
      )}

      {driverStep === "verify" && (
        <form onSubmit={handleSubmit} className="w-full max-w-[320px] flex flex-col gap-4">
          {verifiedToken ? (
            <>
              <h1 className="text-white text-2xl font-extrabold">Confirm your email</h1>
              <p className="text-slate-300/80 text-sm">
                We already confirmed <span className="text-white font-semibold">{email}</span>, no need to verify it again.
              </p>
            </>
          ) : (
            <>
              <h1 className="text-white text-2xl font-extrabold">Verify your email</h1>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="Email address"
                className={inputClass}
              />
              <button
                type="button"
                onClick={handleSendCode}
                disabled={loading}
                className="w-full py-3 rounded-full bg-white/10 border border-white/20 text-white font-semibold"
              >
                {loading ? "Sending…" : codeSent ? "Resend code" : "Send code"}
              </button>
              {codeSent && (
                <input
                  required
                  inputMode="numeric"
                  maxLength={6}
                  value={code}
                  onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))}
                  placeholder="6-digit code"
                  className={inputClass}
                />
              )}
            </>
          )}

          <label className="flex items-start gap-2 text-slate-300 text-xs">
            <input
              type="checkbox"
              required
              checked={agreedToTerms}
              onChange={(e) => setAgreedToTerms(e.target.checked)}
              className="mt-0.5 shrink-0"
            />
            <span>
              I agree to the <a href="/terms" target="_blank" rel="noopener noreferrer" className="underline text-[#1be451]">Terms &amp; Conditions</a> and{" "}
              <a href="/privacy" target="_blank" rel="noopener noreferrer" className="underline text-[#1be451]">Privacy Policy</a>
            </span>
          </label>

          <button
            type="submit"
            disabled={loading || (!verifiedToken && !codeSent) || !agreedToTerms}
            className={`${nextButtonClass} disabled:opacity-50`}
          >
            {loading ? "Submitting…" : "Create account"}
          </button>
        </form>
      )}

      {error && <p className="text-red-400 text-sm">{error}</p>}
    </div>
  );
}
