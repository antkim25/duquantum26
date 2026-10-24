"""Print size and depth of every circuit (free; no job is run).

  python info.py
"""
import bluequbit

bq = bluequbit.init(execution_mode="cloud")  # hidden circuits only run in the cloud; Hybrid machines default to local
for c in ["S1", "S2", "S3", "G1", "G2", "G3", "G4"]:
    try:
        print(c, bq.get_circuit_info(f"Duke_{c}_0"))
    except Exception as e:  # circuits aren't released until kickoff
        print(c, "unavailable:", e)
