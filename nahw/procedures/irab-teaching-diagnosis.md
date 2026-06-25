# Procedure: iʿrāb teaching & diagnosis

**Input:** a token/clause + a learner's (or engine draft's) syntactic analysis.
**Goal:** produce the correct iʿrāb (role · case/mood · governor) for teaching, OR diagnose the
learner/draft error and route to the fix. Conclusion AND reasoning must both be correct.

## Steps
1. **Identify the sentence type** (ismiyya/fiʿliyya) and the clause boundaries.
2. **Assign role + sign** per `references/irab-teaching-map.md`:
   - noun: rafʿ/naṣb/jarr by governor (mubtadaʾ/khabar/fāʿil; mafʿūl/ḥāl/tamyīz; prep/iḍāfa).
   - verb: rafʿ/naṣb/jazm by governor (أن/لن; لم/لا-nāhiya/conditional).
   - diptote: jarr sign = fatḥa.
3. **Check the flippers and near-flippers**: kāna (rafʿ ism/naṣb khabar), kāda and sisters (rafʿ ism;
   khabar is normally an imperfect verb in rafʿ unless another governor changes it), inna (naṣb ism/rafʿ
   khabar), ẓanna (two manṣūb objects), lā of genus (mabnī ism).
4. **Resolve the confusable accusatives**: ḥāl (mushtaqq, state) vs tamyīz (jāmid, respect, fāʿil-convertible);
   istithnāʾ tāmm vs mufarragh.
5. **Check compound numbers and specification**: numbers such as 13-19 are murakkab constructions; the
   counted/specifying noun may be tamyīz manṣūb, and gender agreement belongs to the numbered construction,
   not to a generic noun gloss.
6. **Diagnosis mode**: localize the mismatch, map to a class in
   `references/learner-error-remediation.md`, state the violated rule, give the contrast pair, assign a
   drill, and **reject conclusion-only reasoning** (right answer + wrong iʿrāb = fail).
7. **Output** the iʿrāb object (role, case/mood, sign, governor, reasoning) or the diagnosis object.

## Output object
```json
{"loc":"2:173:18","surface":"عَادٍ","role":"maʿṭūf majrūr","sign":"kasra muqaddara",
 "derivation":"ism fāʿil from عدا","reasoning":"معطوف on باغٍ, majrūr; منقوص","decision":"resolved"}
```

## For the engine
A grammar-affecting gloss requires this object + a second independent agreeing analysis (two-vote).
Uncertain iʿrāb → `pending` with the exact blocker, never a guess.
