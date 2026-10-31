# Sleep Score and Baseline: sources and rules

Research for #14: the basis for the rule-based Sleep Score (#15) and the Baseline (#16). Implemented in `score()` and `baseline()` in `backend/__init__.py`.

## 1. Purpose and scope

The Sleep Score is a single 0-100 number for one finished Sleep Session, always returned with the parts that produced it. It is rule-based with no ML (ADR 0001). It uses four Sensors: heart rate, temperature, humidity and motion. Sound is left out until #11; the WHO noise guidelines (S8, S9) are the named source for a future sound part, and no numbers from them are used now.

The score is a transparent summary of Sensor Readings, not a clinical measure. Weights are a design choice; thresholds come from the sources below where stated.

## 2. Sources

- **S1** Buysse DJ, Reynolds CF, Monk TH, Berman SR, Kupfer DJ. The Pittsburgh Sleep Quality Index: a new instrument for psychiatric practice and research. Psychiatry Res 1989;28(2):193-213. https://doi.org/10.1016/0165-1781(89)90047-4
  Used for: PSQI has 7 components including duration and habitual sleep efficiency (from the abstract). Component bands are duration >7 / 6-7 / 5-6 / <5 h and efficiency >=85 / 75-84 / 65-74 / <65% (from the PSQI scoring sheet, not the paper text).
- **S2** Ohayon M, Wickwire EM, Hirshkowitz M, Albert SM, et al. National Sleep Foundation's sleep quality recommendations: first report. Sleep Health 2017;3(1):6-19. https://doi.org/10.1016/j.sleh.2016.11.006 (open copy: https://escholarship.org/uc/item/9xc5x5h2)
  Used for: sleep efficiency >=85% is good at all ages, <=74% is not good for adults; WASO <=20 min is good (full text).
- **S3** Hirshkowitz M, Whiton K, Albert SM, Alessi C, et al. National Sleep Foundation's sleep time duration recommendations: methodology and results summary. Sleep Health 2015;1(1):40-43. https://doi.org/10.1016/j.sleh.2014.12.010
  Used for: 7-9 h for adults (abstract). The 6 h and 10 h "may be appropriate" tier is from the NSF press release of 2 Feb 2015, https://www.eurekalert.org/news-releases/554948. The full text was not read.
- **S4** Cole RJ, Kripke DF, Gruen W, Mullaney DJ, Gillin JC. Automatic sleep/wake identification from wrist activity. Sleep 1992;15(5):461-469. https://doi.org/10.1093/sleep/15.5.461
  Used for: the idea of scoring wake from neighbouring epochs by rule, about 88% agreement with PSG (abstract). Its coefficients are not used (they are device-specific counts).
- **S5** Sadeh A, Sharkey KM, Carskadon MA. Activity-based sleep-wake identification: an empirical test of methodological issues. Sleep 1994;17(3):201-207. https://doi.org/10.1093/sleep/17.3.201
  Used for: 91-93% agreement with PSG; actigraphy under-detects wake (abstract).
- **S6** Ben-Dov IZ, Kark JD, Ben-Ishay D, Mekler J, Ben-Arie L, Bursztyn M. Blunted heart rate dip during sleep and all-cause mortality. Arch Intern Med 2007;167(19):2116-2121. https://doi.org/10.1001/archinte.167.19.2116
  Used for: nondipping is (awake - sleep) / awake < 0.1; mortality rises linearly as the dip falls (abstract).
- **S7** Okamoto-Mizuno K, Mizuno K. Effects of thermal environment on sleep and circadian rhythm. J Physiol Anthropol 2012;31:14. https://doi.org/10.1186/1880-6805-31-14 (open: https://pmc.ncbi.nlm.nih.gov/articles/PMC3427038/)
  Used for: 13-23 degC with bedding gives no significant sleep-stage change; humid heat disturbs sleep; bed microclimate is 32-34 degC and 40-60% RH (full text).
- **S8** WHO Regional Office for Europe. Night noise guidelines for Europe, 2009. https://www.who.int/europe/publications/i/item/9789289041737
  Future sound part only.
- **S9** WHO Regional Office for Europe. Environmental noise guidelines for the European Region, 2018. https://www.who.int/europe/publications/i/item/9789289053563
  Future sound part only; no values quoted.

## 3. Formula

total = round(sum of points / sum of max x 100) over the parts that are not excluded.

| Part | Max | Rule | Thresholds | Source | Design choice |
|---|---|---|---|---|---|
| duration | 30 | time in bed h = ended_at - started_at | 7-9 h: 30; 6-<7 or >9-10: 20; 5-<6 or >10: 10; <5: 0 | S3, S1 | band points, >10 h = 10 |
| restlessness | 30 | share of wake-like motion epochs | efficiency >=85%: 30; 75-<85: 20; 65-<75: 10; <65: 0 | S2, S1; S4/S5 for the idea | neighbour rule, step points |
| heart_rate | 20 | dip from first 30 min to lowest hour | 20 x clamp(dip / 0.10, 0, 1) | S6 | linear scale, pre-sleep proxy |
| environment | 20 | share of Readings in range | temperature 13-23 degC, humidity 40-60% RH; 10 x temp share + 10 x humidity share | S7 | 10/10 split, humidity as room proxy |

Weights 30/30/20/20 are a design choice.

## 4. Per-part rules

**Duration.** Time in bed, not measured sleep (the Sensors cannot tell). Always scored.

**Restlessness.** Epochs are the motion Readings in time order. An epoch is wake-like when its value is above 0 and the previous or next epoch is also above 0, so an isolated movement does not count. This is a simplified neighbour rule inspired by S4 and S5; it is not their coefficients and has not been validated against PSG. Efficiency estimate = 1 - wake-like / epochs. Actigraphy under-detects wake (S5), so the estimate leans optimistic.

**Heart rate.** Awake = mean heart rate over the 30 min from the first heart-rate Reading. Sleep = lowest mean of hourly buckets counted from the first heart-rate Reading. Dip = (awake - sleep) / awake. S6 defines the dip against daytime heart rate; there is no daytime heart rate here, so the pre-sleep half hour is a proxy. That is a design choice and stricter than S6, because pre-sleep heart rate is usually lower than daytime heart rate. A rise gives a negative dip and 0 points.

**Environment.** Temperature share = share of temperature Readings in 13-23 degC. Humidity share = share of humidity Readings in 40-60% RH. S7 gives 40-60% for the bed microclimate, not the room; it is used for the room as a design choice.

## 5. Missing data

- A Sensor is unusable when its Data Gaps add up to more than 50% of the Sleep Session, or the session length is 0. Exactly 50% is usable. A Sensor with no Readings is one whole-session Data Gap.
- A part whose Sensor is unusable is excluded and the total is rescaled over the remaining parts.
- Environment uses one Sensor if only one is usable (20 x its share); with neither, it is excluded.
- Duration is never excluded.
- The score is null while a Sleep Session is running, and when restlessness, heart_rate and environment are all excluded: no Sensor data means no score, never a score from duration alone.

## 6. Output shape

```json
{
  "total": 76,
  "parts": [{"name": "duration", "points": 30.0, "max": 30, "detail": "8 h 0 min in bed; NSF recommends 7-9 h for adults"}],
  "excluded": ["heart_rate"]
}
```

`parts` and `excluded` use the fixed order duration, restlessness, heart_rate, environment. `points` is rounded to 1 decimal. `score` is null for a running Sleep Session.

## 7. Baseline

The Baseline is the mean of the Sleeper's last 7 earlier Sleep Sessions that were finished, not Auto-closed Sessions, and scored (score not null). "Earlier" means started before the current one; the current session is never included. Computed for running sessions too.

- Fewer than 3 such sessions: no Baseline, with reason "Baseline still building: n of 3 past Sleep Sessions".
- Otherwise: `total` = mean of totals, `parts` = mean points per part, `sessions_used` = n, all rounded to 1 decimal. A part's mean skips sessions that excluded that part; a part no session scored is absent.

## 8. Design choices and open items

- Weights 30/30/20/20 are not from a source.
- The heart-rate scale is linear; S6 gives the 10% cut-off, not a point scale.
- More than 10 h in bed scores 10, the same as 5-6 h; S3 does not tier long sleep that way.
- The environment 10/10 split and the use of bed-microclimate humidity for the room are choices.
- Band points are steps, so the score jumps at band edges (for example 84.9% vs 85% efficiency).
- The scores are not validated against PSG or any outcome.
- Sound joins the formula after #11, which means re-weighting.

## 9. Expected Scenario scores

Measured with `score()` on Simulator 8 h nights, seeds 1-5, no Data Gaps. Total, with part points (duration / restlessness / heart_rate / environment) for seed 1.

| Scenario | Seed 1 | Seed 2 | Seed 3 | Seed 4 | Seed 5 | Seed 1 parts |
|---|---|---|---|---|---|---|
| good | 100 | 100 | 100 | 100 | 100 | 30 / 30 / 20 / 20 |
| restless | 76 | 76 | 76 | 76 | 76 | 30 / 20 / 6.3 / 20 |
| hot-humid | 73 | 74 | 73 | 74 | 76 | 30 / 30 / 13.0 / 0 |
