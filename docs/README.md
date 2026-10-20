# Repository documentation

Prepared October 19, 2026, from the local working tree. The current desktop
package declares version **0.1.3**. The last commit at inspection was
`219e38b` (`Prepare Windows installer release 0.1.2`), and implementation changes
were already present locally. These documents describe those inspected files,
not an assertion that every change has been committed or released.

## Read in this order

1. [Presentation guide](PRESENTATION_GUIDE.md): learn the explanation you can
   deliver to your audience, then practice the questions at the end.
2. [Technical reference](TECHNICAL_REFERENCE.md): study the exact implementation,
   formulas, thresholds, component responsibilities, and operational details.
3. [Validation report](VALIDATION_REPORT.md): use the verified numbers and their
   limitations when discussing research findings.

## The central explanation

The HITL desktop is a local essay-assessment decision-support application. Python
extracts interpretable language measurements, Llama 3 supplies rubric-based
judgments, and a human rater accepts or changes the recommended grade before
the completed workbook is saved.

**The deployed score flow is:** LLM recommendation → human final score → placement.
The linguistic indicators provide evidence and mismatch alerts. A separate
research script tests learned Ridge combinations of the linguistic and LLM
features; that learned model is not loaded by the desktop scoring path.

## Existing operational documentation

- [Standalone extractor usage](../README.md)
- [HITL usage and app API](../HITL/README.md)
- [Electron development and packaging](../HITL/desktop/README.md)
- [Windows handoff](../HITL/WINDOWS_HANDOFF.md)
- [macOS handoff](../HITL/MAC_HANDOFF.md)
- [Packaging plan](../HITL/packaging/PACKAGING_PLAN.md)
- [Experimental hybrid workflow](../hybrid%20LLM%20AES/README.md)
- [React prototype](../prototype-ui/README.md)
- [Colab workflow](../GColab%20Version/README.md)

Some older documents describe earlier stages of development. When descriptions
conflict, the source files linked in the technical reference establish what the
inspected implementation does. In particular, the Electron desktop, the React
prototype, and the NewAes/Colab batch scorers are different execution paths.
