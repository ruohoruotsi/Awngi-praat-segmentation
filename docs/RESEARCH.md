
## Prior Research For Computational Detection Of Acoustic/Linguistic Measures

### Burst

- [Automatic classification of stop realisation with wav2vec2.0](https://www.isca-archive.org/interspeech_2025/tanner25_interspeech.pdf)

- [A module for automatic analysis of burst spectra for consonant plac detection](https://www.researchgate.net/publication/381968596_A_module_for_automatic_analysis_of_burst_spectra_for_consonant_place_detection)

- [An Exemplar-based Approach to Automatic Burst Detection in Spontaneous Speech](https://escholarship.org/uc/item/7f3546t9)

- [Detection of the closure-burst transitions of stops and affricates in continuous speech using the plosion index](https://pubs.aip.org/asa/jasa/article-abstract/135/1/460/564598/Detection-of-the-closure-burst-transitions-of?redirectedFrom=fulltext)

- [Automatic Phonetic Transcription in Two Steps: Forced Alignment and Burst Detection](https://www.researchgate.net/publication/269083905_Automatic_Phonetic_Transcription_in_Two_Steps_Forced_Alignment_and_Burst_Detection)



### VOT
- [Automatic detection of Voice Onset Time in voiceless plosives using gated recurrent units](https://www.sciencedirect.com/science/article/abs/pii/S105120042030124X)
- [Automatic measurement of voice onset time using discriminative structured prediction](https://pubs.aip.org/asa/jasa/article-abstract/132/6/3965/915621/Automatic-measurement-of-voice-onset-time-using?redirectedFrom=fulltext)
- [Automatic voice onset time detection for unvoiced stops
(/p/,/t/,/k/) with application to accent classification](https://personal.utdallas.edu/~jxh052100/Publications/JP-71-SpeechComm-Hansen-Gray-Kim-VOT-Oct2010.pdf)

- [wav2VOT: Automatic estimation of voice onset time, closure duration, and burst realisation with wav2vec2](https://arxiv.org/abs/2606.28857v1)
- [Automatic Measurement of Voice Onset Time and Prevoicing using Recurrent Neural Networks](https://pmc.ncbi.nlm.nih.gov/articles/PMC12981358/)

- [Automatic Detection of Voice Onset Time Contrasts for Use in Pronunciation Assessment](https://www.isca-archive.org/interspeech_2006/kazemzadeh06_interspeech.pdf)


---

### Linguistic Feedback

1. Among the reviewed studies, I find the plosion-index approach of Ananthapadmanabha et al. (2014), the automatic VOT estimation approaches of Sonderegger and Keshet (2012) and Adi et al. (2016), and the wav2vec2-based approach of Tanner et al. (2025) particularly relevant.

One important distinction is that detecting the presence of a burst, identifying its precise temporal boundaries, and estimating VOT are related but different computational tasks. I think combining insights from these approaches could provide a useful foundation for our work.

2. Phonetic characteristics of Awngi &rarr;

    Awngi presents some interesting challenges for computational annotation. The target inventory consists of ten stops: `/p, b, t, d, k, ɡ, q, kʷ, ɡʷ, qʷ/`, including uvular and labialized consonants that are not always represented in the language datasets used to develop existing tools.
    
The presence of these consonants, together with differences in voicing and place of articulation, may influence burst spectra, release characteristics and adjacent-vowel formant transitions. The voicing categories are also not symmetrical across all places of articulation.

Therefore, I believe that existing computational methods should be adapted and evaluated against manually verified Awngi annotations rather than transferred directly from other languages without validation.

This language-specific aspect makes the project particularly interesting and potentially valuable for computational phonetics of under-resourced Ethiopian languages.


### Implementation priority and development sequence

Let's develop the computational workflow in two consecutive phases rather than implementing both word positions simultaneously.

#### Phase 1: Word-initial stops (first priority)
I would like to begin with automatic burst detection, release-boundary identification and VOT estimation for word-initial stops. The system should generate the corresponding Praat TextGrid with Word, Consonant, Vowel, Burst and VOT tiers. Closure duration will not be measured for these tokens.

We can initially test the system using representative word-initial tokens and compare its proposed boundaries and measurements with the manually verified annotations.

#### Phase 2: Intervocalic stops (second priority)
Once the word-initial workflow has been successfully tested and validated, we can extend the system to intervocalic stops. This phase should focus on identifying the preceding-vowel offset, closure onset and release burst, calculating closure duration, and classifying closure voicing as continuous, partial or absent. The corresponding TextGrid should contain Word, Consonant, Vowel, Closure duration, Burst and Closure voicing tiers. Conventional VOT will not be calculated for these tokens.

This sequential approach will allow us to establish a reliable annotation procedure for word-initial stops first, evaluate its performance, and then adapt the computational workflow to the different acoustic characteristics of intervocalic stops.

--- 

Acoustic Characteristics of Awngi Stops, automatic acoustic annotation would be particularly valuable because I have approximately 3,840 speech tokens to annotate and analyze.

I would suggest prioritizing the following tasks:

1. **Automatic burst detection** &rarr; Identify potential stop-release bursts in both word-initial and intervocalic stops, providing preliminary onset and offset boundaries with confidence scores.
2. **Word-initial VOT estimation** &rarr; Automatically identify the release point and the onset of regular periodic voicing, and calculate VOT, including negative VOT where prevoicing is present. Closure duration is not measured as an acoustic outcome for word-initial stops in the research protocol.
3. **Intervocalic closure analysis** &rarr; Identify the offset of the preceding vowel, the onset of stop closure and the release burst to estimate closure duration. It would also be useful to classify closure voicing as continuous, partial or absent. Conventional VOT is not used as a numerical measurement for intervocalic stops in the current research protocol.
4. **Praat TextGrid generation and position-specific annotation**: I would prefer the software to generate two position-specific Praat TextGrid templates, as the temporal measurements differ between word-initial and intervocalic stops.

    <br/>
   
   **A. Word-initial stops**, the preferred annotation tiers are &rarr;

      - Word
      - Consonant
      - Vowel
      - Burst
      - VOT
       
      The system should identify the complete word and target consonant boundaries, the following vowel, the release-burst interval, and the VOT interval. VOT should be calculated from the release point to the onset of regular periodic voicing. Closure duration should not be measured for these tokens.
   
    <br/>
   
   **B. Intervocalic stops**, the preferred annotation tiers are &rarr;
       
      - Word
      - Consonant
      - Vowel
      - Closure duration
      - Burst
      - Closure voicing
       
   The system should identify the complete word and target consonant boundaries, the preceding and following vowels, the closure onset and release, the closure-duration interval, and the release-burst interval. Closure voicing should be classified as continuous, partial or absent. Conventional VOT should not be calculated as a numerical outcome for these tokens.

If a uniform TextGrid structure is required for computational processing, a VOT tier may be retained in intervocalic files for structural consistency, but it should be marked as not applicable rather than populated with numerical VOT values.

In both templates, the word, consonant, vowel and burst annotations should follow consistent labelling and boundary conventions. The position-specific temporal measurements should remain separate.


5. **Acoustic feature extraction** &rarr; After manual verification of the annotated boundaries, the system should support automatic extraction of:

    - Relative burst amplitude
    - Spectral moments
    - Cepstral coefficients
    - F2 and F3 formant transitions
    
   These measurements will support the investigations of voicing, place of articulation and the acoustic characteristics of plain and labialized stops.

6. **Pilot testing and validation** &rarr; I would particularly appreciate beginning with a pilot dataset representing different Awngi stop categories and both word positions. We could compare the automatic estimates with manually verified annotations before applying the procedure to the complete dataset.


### Validation
The validation should assess boundary-detection accuracy, burst-detection performance, VOT and closure-duration measurement errors, and the reliability of closure-voicing classification. Uncertain tokens should be flagged for manual inspection.

The main objective is to ***reduce repetitive annotation work while maintaining phonetic accuracy***, consistency and reliability. I would therefore prefer a semi-automatic approach in which the software proposes boundaries and measurements, while I retain final control over the phonetic annotations.

This would be a very practical computational contribution.