import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { getDriverPayouts, getDriverSummary, type DriverSummaryOut, type PayoutOut } from "../api/rides";

export default function Balance() {
  const { accessToken } = useAuth();
  const navigate = useNavigate();
  const [summary, setSummary] = useState<DriverSummaryOut | null>(null);
  const [payouts, setPayouts] = useState<PayoutOut[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!accessToken) return;
    Promise.all([getDriverSummary(accessToken), getDriverPayouts(accessToken)])
      .then(([s, p]) => {
        setSummary(s);
        setPayouts(p);
      })
      .catch(() => setError("Could not load your balance."));
  }, [accessToken]);

  return (
    <div className="fixed inset-0 flex flex-col bg-[#20241f] text-slate-100">
      <div className="flex items-center gap-3 px-4 pt-6 pb-4">
        <button
          onClick={() => navigate("/driver")}
          className="w-9 h-9 rounded-full bg-white/10 flex items-center justify-center"
          aria-label="Back"
        >
          <i className="fa-solid fa-arrow-left" />
        </button>
        <h1 className="text-white text-xl font-extrabold">Balance</h1>
      </div>

      <div className="flex-1 overflow-y-auto px-4 pb-8 flex flex-col gap-4">
        {error && <p className="text-red-400 text-sm text-center mt-4">{error}</p>}

        {summary && (
          <>
            <div className="rounded-2xl bg-white/5 border border-white/10 p-5 flex flex-col gap-1">
              <p className="text-slate-400 text-xs">Today's earnings</p>
              <p className="text-white text-3xl font-extrabold">₦{summary.todays_earnings.toLocaleString()}</p>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="rounded-2xl bg-white/5 border border-white/10 p-4">
                <p className="text-slate-400 text-xs">All-time earnings</p>
                <p className="text-white text-lg font-bold">₦{summary.total_earnings.toLocaleString()}</p>
              </div>
              <div className="rounded-2xl bg-white/5 border border-white/10 p-4">
                <p className="text-slate-400 text-xs">Rides completed</p>
                <p className="text-white text-lg font-bold">{summary.completed_trips}</p>
              </div>
              <div className="rounded-2xl bg-white/5 border border-white/10 p-4">
                <p className="text-slate-400 text-xs">Completion rate</p>
                <p className="text-white text-lg font-bold">{summary.completion_rate}%</p>
              </div>
              {summary.cash_debt > 0 && (
                <div className="rounded-2xl bg-white/5 border border-white/10 p-4">
                  <p className="text-slate-400 text-xs">Cash commission owed</p>
                  <p className={`text-lg font-bold ${summary.cash_debt_blocked ? "text-red-400" : "text-amber-400"}`}>
                    ₦{summary.cash_debt.toLocaleString()}
                  </p>
                </div>
              )}
            </div>

            <div>
              <h2 className="text-white font-semibold mb-2">Payouts</h2>
              {payouts.length === 0 ? (
                <p className="text-slate-400 text-sm">
                  No card-paid trips yet. Cash trips are paid to you directly.
                </p>
              ) : (
                <div className="flex flex-col gap-2">
                  {payouts.map((p) => (
                    <div
                      key={p.id}
                      className="rounded-2xl bg-white/5 border border-white/10 p-3 flex items-center justify-between"
                    >
                      <div>
                        <p className="text-white text-sm font-semibold">Ride #{p.ride_id}</p>
                        <p className="text-slate-400 text-xs">
                          {new Date(p.created_at).toLocaleDateString(undefined, {
                            day: "numeric", month: "short", year: "numeric",
                          })}
                        </p>
                      </div>
                      <div className="text-right">
                        <p className="text-white font-semibold">₦{p.amount.toLocaleString()}</p>
                        <p
                          className={`text-xs ${
                            p.status === "paid"
                              ? "text-[#1be451]"
                              : p.status === "failed"
                                ? "text-red-400"
                                : "text-amber-400"
                          }`}
                        >
                          {p.status}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
