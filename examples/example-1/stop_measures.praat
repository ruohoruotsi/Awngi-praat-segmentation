# ============================================================================
# stop_measures.praat — in-Praat cross-check of VOT & closure duration
# ----------------------------------------------------------------------------
# The Python engine (python -m pipeline measure) is the source of truth for
# measurements; this script lets you verify a few stops interactively inside
# Praat, right where you annotated.
#
# HOW TO USE
#   1. In Praat: File > Open... and choose your clip .wav (or the master wav).
#      A .TextGrid with the SAME name in the SAME folder is attached
#      automatically by Praat.
#   2. In the "Praat objects" window, select BOTH the Sound and the TextGrid.
#   3. File > Open praat script... choose this file, then Run.
#   4. Results appear in the Info window (View > Show the info).
#
# Expected tiers: "Sound" (stop labels) and "Events" (CO/BR/VO marker boxes;
# a marker's time = the middle of its box).
# ============================================================================

if not selected("Sound") then
	call exit "Select your Sound object first (File > Open... your .wav)."
endif
if not selected("TextGrid") then
	call exit "Also select the TextGrid in Praat objects (open the .wav and its .TextGrid together)."
endif

string	sndName$ = selected("Sound")
integer	tg       = selected("TextGrid")

integer	soundTier  = tg Get tier number from name "Sound"
integer	eventsTier = tg Get tier number from name "Events"
if soundTier == 0 then
	call exit 'Could not find a tier named "Sound".'
endif
if eventsTier == 0 then
	call exit 'Could not find a tier named "Events" (mark CO/BR/VO first).'
endif

integer	nStops = tg Get number of intervals soundTier
print "Stop measures from " sndName$
print ""
print "stop    t(CO)   t(BR)   t(VO)   closure(ms)   VOT(ms)"

integer	printed = 0
for i in 1..nStops {
	string	label$ = tg Get label at time soundTier (tg Get interval start soundTier i + 0.5 * (tg Get interval end soundTier i - tg Get interval start soundTier i))
	if label$ == "" then
		nexti
	endif
	real	stopMid = tg Get interval start soundTier i + 0.5 * (tg Get interval end soundTier i - tg Get interval start soundTier i)

	# scan the Events tier for CO / BR / VO boxes near this stop
	real	tCO = -1
	real	tBR = -1
	real	tVO = -1
	integer	nEvents = tg Get number of intervals eventsTier
	for j in 1..nEvents {
		string	elabel$ = tg Get label at time eventsTier (tg Get interval start eventsTier j + 0.5 * (tg Get interval end eventsTier j - tg Get interval start eventsTier j))
		if elabel$ == "" then
			nextj
		endif
		real	eMid = tg Get interval start eventsTier j + 0.5 * (tg Get interval end eventsTier j - tg Get interval start eventsTier j)
		# marker must sit inside the stop box, or up to 350 ms after it (VOT runs into the vowel)
		if eMid < tg Get interval start soundTier i - 0.15 then
			nextj
		endif
		if eMid > tg Get interval end soundTier i + 0.35 then
			nextj
		endif
		if elabel$ == "CO" then
			tCO = eMid
		elseif elabel$ == "BR" then
			tBR = eMid
		elseif elabel$ == "VO" then
			tVO = eMid
		endif
	}

	real	closureMs = -9999
	real	votMs     = -9999
	if tCO >= 0 and tBR >= 0 then
		closureMs = (tBR - tCO) * 1000
	endif
	if tBR >= 0 and tVO >= 0 then
		votMs = (tVO - tBR) * 1000
	endif

	print label$ "    "
	if tCO >= 0 then
		print tCO "   "
	else
		print "-       "
	endif
	if tBR >= 0 then
		print tBR "   "
	else
		print "-       "
	endif
	if tVO >= 0 then
		print tVO "   "
	else
		print "-       "
	endif
	if closureMs >= 0 then
		print closureMs "    " votMs
	else
		print "no CO/BR" "    no BR/VO"
	endif
	printed = printed + 1
}
if printed == 0 then
	print "(no labelled stops on the Sound tier yet)"
endif
print ""
print "VOT in ms: positive = voicing starts AFTER the burst, negative = pre-voiced."
