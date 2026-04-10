======================================================================
PATENT LEGAL ANALYSIS - EPO + NIPO
======================================================================

EXAMINATION DECISION: OBJECT
RISK LEVEL: HIGH

The application lacks essential enablement details (analog integrator specs, timing parameters, calibration algorithms, digital control architecture, host interface protocol) and contains unclear claim language (vague terms, functional wording, overly broad scope). While support is adequate, the combined enablement and clarity deficiencies constitute a high risk of rejection.

======================================================================
FORMAL EXAMINATION REPORT
======================================================================

**Examination Report – Formal Objection**  

The European Patent Office’s Regulations to the Norwegian Patents Act, in conjunction with the Norwegian Patents Act, require that a patent application (i) disclose the invention in a manner sufficiently clear and complete for a person skilled in the art to carry it out (Art. 71 (1) NP Act, corresponding to Art. 83 EPC); (ii) define the claimed subject‑matter in a clear and unambiguous way (Regulations §§ 4.1, 4.6, 4.10); and (iii) be supported by the description (Norwegian Patents Act, Section 8).  

1. **Enablement (Art. 71 (1) NP Act / Art. 83 EPC)** – The independent claims recite a “plurality of logical computation channels … greater than the number of physical analog computation elements” and a “continuous‑time mathematical‑operation fabric” without providing the essential technical parameters required to reproduce the system over the full claimed scope. The description contains only high‑level block diagrams and functional statements; it omits:

   * quantitative specifications of the analog integrator circuits (component values, op‑amp models, bandwidth, and design rules for the TDM switching network);  
   * exact timing parameters for the time‑domain multiplexing (slot length, settling time, jitter tolerances, allowable skew);  
   * a complete calibration methodology (algorithmic steps, reference standards, frequency of recalibration, storage format of correction coefficients);  
   * structural details of the digital control subsystem (FPGA/SoM resource allocation, state‑machine diagram, register map, firmware interfaces); and  
   * a defined host‑interface protocol (e.g., PCI‑Express Gen 3 lane count, register map, DMA timing).

   Consequently, a skilled person would be faced with an undue burden to determine the means for achieving the claimed functions, which is a clear breach of the enablement requirement. The deficiencies are classified as **critical** (see detailed issues § 1.2 and § 1.1 of the analysis).  

2. **Clarity of the claims (Regulations §§ 4.1, 4.6, 4.10)** – The claims suffer from multiple clarity defects:

   * Use of vague relative terms such as “high‑speed” (claim 8) without quantitative definition, violating § 4.6.  
   * Undefined technical terms “non‑idealities”, “logical computation channels”, and “analog computation fabric” (claims 1, 5), contravening § 4.1.  
   * Overly functional language (“configured to perform continuous‑time mathematical operations”, “configured to control, schedule, and supervise operation”) that does not recite structural features, breaching § 4.1.  
   * Result‑to‑be‑achieved phrasing in claim 10 (“execute differential equation solving, optimisation, control, or signal‑processing tasks”) without reciting the means to obtain that result, in violation of § 4.10.  

   These ambiguities render the claims unclear to the skilled person and therefore non‑compliant with the statutory clarity provisions. The most serious deficiencies are marked **critical** (functional language) and **moderate** (relative term “high‑speed”).  

3. **Support by the description (Norwegian Patents Act, Section 8)** – The analysis confirms that all claim features have a basis in the disclosed embodiments; the support requirement is satisfied.  

**Conclusion**  

The application, in its present form, does **not** satisfy the enablement requirement of Art. 71 (1) NP Act (Art. 83 EPC) and fails to meet the clarity standards of the Regulations §§ 4.1, 4.6, 4.10. Accordingly, the claims are rejected insofar as they stand.  

**Required amendments**  

* Provide detailed schematics of the analog integrators (including component values, op‑amp models, and bandwidth), and specify the design rules for the TDM switching network (switch resistance, charge‑injection limits, maximum channel‑to‑element ratio).  
* State the exact time‑slot duration, required analog settling time, jitter and skew tolerances, and include timing diagrams illustrating the multiplexing schedule.  
* Describe the calibration routine in full, with algorithmic steps, reference standards, frequency of recalibration, and the format of correction coefficients.  
* Disclose the digital control subsystem architecture (resource allocation, state‑machine diagram, register definitions, example HDL snippets) and the host‑interface protocol (PCI‑Express generation, lane count, register map, DMA parameters).  
* Replace vague and functional language with concrete structural features, e.g., “comprising a digital control unit including a programmable logic device that generates control signals for the analog computation fabric” and define “high‑speed” by a quantitative data‑rate (e.g., ≥ 10 GB/s).  
* Re‑phrase result‑to‑be‑achieved claims to recite the structural means that enable the stated tasks.  

The applicant is invited to file a complete amendment addressing the above deficiencies within the statutory time limit. Failure to do so will result in the final refusal of the application.


======================================================================
ENABLEMENT (Art. 83 EPC / §8)
======================================================================
Status: NOT_ENABLED
Reason: Fails §1.2 Level of details and §1.3 Objections under Art. 83 – the disclosure lacks essential technical parameters and concrete implementation steps required for a skilled person to reproduce the system across the full claimed scope.
Reproducibility: 28.0%

Missing Elements:
  • Analog integrator circuit topologies, component values, and bandwidth specifications.
  • Exact time‑slot duration, required analog settling time, and allowable timing skew.
  • Calibration sequence steps, reference standards, frequency of recalibration, and storage format of correction coefficients.
  • FPGA/SoM resource allocation, control logic flowcharts, and timing diagrams for scheduling.
  • PCIe (or alternative) register map, command set, and DMA transfer parameters.

======================================================================
CLARITY (Art. 84 EPC)
======================================================================
Status: UNCLEAR
Reason: Multiple clarity defects: vague relative terms, undefined functional language and result‑to‑be‑achieved wording violate §§4.1, 4.6 and 4.10.
Clarity Score: 38.0%

Vague Terms:
  • high‑speed

======================================================================
SUPPORT (Art. 84 EPC)
======================================================================
Status: SUPPORTED
Reason: All claim features have a basis in the description; the scope does not exceed what is disclosed (§6.1 General Support).
Support Score: 95.0%

--- Detailed Enablement Violations ---
[CRITICAL] Citation: §1.2 Level of details
          Reason: The description provides only high‑level block diagrams and generic functional statements. A skilled person cannot reproduce the analog fabric, timing, or calibration without specific circuit parameters, timing budgets, and algorithmic steps, leading to an undue burden.
          Suggestion: Add detailed schematics of the analog integrators (capacitor, resistor values, op‑amp models), specify the TDM slot length (e.g., 10 µs) and required settling time (e.g., 2 µs), and include a flowchart of the calibration routine with measurement points and coefficient calculation formulas.
[MODERATE] Citation: §1.3 Objections under Art. 83
          Reason: The application asserts that the system can compute “continuous‑time mathematical operations” across an arbitrary number of logical channels but does not disclose the means to achieve this across the entire claimed range (e.g., how many channels can be supported, how performance scales). This is a result‑oriented description lacking enabling means.
          Suggestion: Provide a scalability analysis showing the maximum channel‑to‑element ratio, including switching network specifications, crosstalk limits, and timing constraints, together with example configurations (e.g., 8 logical channels on 2 integrators).
[CRITICAL] Citation: §1.1 General Principle
          Reason: The overall disclosure does not meet the requirement of being “sufficiently clear and complete” because key implementation details (digital control firmware, host‑interface protocol) are omitted, preventing a skilled person from carrying out the invention.
          Suggestion: Include a detailed description of the digital control subsystem: state‑machine diagram, register definitions, timing of control signals, and example HDL code snippets. Also, specify the host interface protocol (PCIe Gen3, lane count, register map).

--- Detailed Clarity Violations ---
[CRITICAL] Citation: §4.1
          Reason: The claim uses functional wording such as "configured to perform" and "configured to control, schedule, and supervise" without reciting structural features that achieve these functions. This makes the claim unclear to the skilled person.
          Suggestion: Replace functional language with concrete structural elements, e.g., "comprising a digital control unit comprising a programmable logic device configured to generate control signals for the analog computation fabric".
[MODERATE] Citation: §4.6
          Reason: "high‑speed peripheral interconnect" is a relative term. Its technical meaning is not objectively defined in the claim, rendering it unclear.
          Suggestion: Specify a quantitative parameter, e.g., "a peripheral interconnect having a data rate of at least 10 GB/s".
[CRITICAL] Citation: §4.10
          Reason: Claim 10 defines the invention in terms of a result to be achieved ("execute differential equation solving, optimization, control, or signal processing tasks") without providing the means to achieve that result across the full scope.
          Suggestion: Re‑phrase to recite the structural means that enable those tasks, e.g., "wherein the analog computation fabric comprises a network of integrators that, when driven by the digital control subsystem, solves differential equations".
[MODERATE] Citation: §4.6
          Reason: The term "non‑idealities" is undefined; the skilled person cannot determine which non‑idealities are covered (gain error, offset, drift, etc.).
          Suggestion: Define the term in the claim or replace with specific parameters, e.g., "measure and compensate for gain error, offset voltage, temperature drift, and component mismatch".
[MODERATE] Citation: §4.1
          Reason: The phrase "hardware accelerator card installable in a computing system" is functional and does not describe the structural features that make the system an accelerator card.
          Suggestion: Add structural features, e.g., "comprising a printed circuit board having a PCI‑Express form factor and a power connector".

======================================================================
CRITICAL ISSUES
======================================================================
  🚨 Insufficient quantitative and structural details to enable the analog computation fabric and its time‑domain multiplexing.
  🚨 Missing timing specifications (slot length, settling time, jitter tolerances) for reliable operation.
  🚨 Calibration methodology is only conceptual; no algorithms, sequences, or coefficient ranges are disclosed.
  🚨 Digital control subsystem and host interface lack architectural description, state‑machine flow, and protocol/register specifications.
  🚨 Claims use vague and functional language (e.g., "high‑speed", "non‑idealities", "configured to perform…") leading to lack of clarity and over‑broad scope.

======================================================================
RECOMMENDATIONS
======================================================================
  1. Provide complete circuit diagrams with component values, bandwidth, and integrator topology details.
  2. Specify exact time‑slot durations, required analog settling times, jitter tolerances, and timing diagrams for the multiplexing mechanism.
  3. Include detailed calibration procedures: reference standards, step‑by‑step sequences, algorithmic description, frequency of recalibration, and storage format of correction coefficients.
  4. Describe the digital control subsystem architecture (FPGA/SoC resource allocation, state‑machine flowcharts, firmware interfaces) and supply timing diagrams for scheduling.
  5. Define all functional terms in the claims, replace vague language with concrete technical features, and narrow claim scope to match the disclosed embodiments.

======================================================================
