# Project video script (target 4 minutes)

About 130 spoken words per minute. Each block names the slide to show. Split the speaking parts between team members.

---

**0:00-0:25 | Slide 1 (title)**
"Hi, we are team [name]. Our project is called *Invisible Exposure*. Climate-risk tools count how many buildings sit in heat, wildfire and drought zones using open maps. If a map is missing buildings, those buildings, and the people in them, are missing from the risk count. We asked: where is the open map incomplete, who lives there, and is it getting better?"

**0:25-0:55 | Slide 2 (problem)**
"The hard part is that you usually need a perfect reference map to measure incompleteness, and one rarely exists. So our problem statement is: estimate, without a perfect reference and with honest uncertainty, where Overture Maps is incomplete for every census tract; turn those gaps into hidden climate exposure; and test, with a pre-registered plan, whether the gaps fall on vulnerable, rural and tribal communities."

**0:55-1:30 | Slide 3 (data) + Slide 4 (method)**
"We studied 9,794 census tracts in five hazard regions: Arizona, northern California, Oklahoma, Texas and Washington, with 19 million Overture buildings and three releases from 2023 to 2026. Our model predicts how many buildings and places a tract *should* have, using only neutral facts like housing units, population and jobs. Vulnerability and hazard data are never model inputs; a code guard blocks them. We use conformal prediction to put a calibrated 90% range around every prediction, and we flag tracts that fall below it."

**1:30-2:10 | Slide 5 (validation)**
"Does it work? The ranges hold 90.0% of tracts, exactly the target. But if we move the model to a region it has never seen, coverage drops to 84.6%, so local calibration matters. Against the independent FEMA/ORNL USA Structures inventory, our flags are five times more likely than chance to be real gaps, and if we delete half of a tract's buildings, the model catches it 96% of the time."

**2:10-3:00 | Slide 6 (catch-up) + Slide 7 (regression)**
"Good news first: between 2023 and 2026, the map caught up. Rural tracts improved almost ten percentage points more than urban ones. Then we found something nobody had reported: from the September 2026 release onward, Overture silently dropped about 179,000 buildings around San Antonio, in tracts where 889,000 people live and most are highly vulnerable. Our model, using no reference at all, flagged 82% of those tracts. So this method can monitor every new map release."

**3:00-3:35 | Slide 8 (hidden exposure + limitation)**
"Missing buildings in high-wildfire areas are almost five times more common per home in rural tracts than urban ones. We also found an honest limitation: tract-level flags miss gaps that a whole group shares, because the model learns that shortfall as normal. So fairness audits need a reference comparison as well."

**3:35-4:00 | Slide 9 (conclusion)**
"To sum up: calibrated completeness estimates, a real release regression detected, rural catch-up confirmed, and a clear warning about what such models cannot see. All code, data links and the paper are in our GitHub repository, and everything reproduces with one command. Thank you."

---

**Recording tips:** record slides with Zoom, Teams or OBS screen-share; keep the camera on in a corner; aim for 3:45-4:15; export as MP4.
