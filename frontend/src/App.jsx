import { ThemeProvider } from './context/ThemeContext'
import WizardLayout from './components/WizardLayout'
import Step1Residency from './steps/Step1Residency'
import Step2Assets from './steps/Step2Assets'
import Step3Goals from './steps/Step3Goals'
import Step4Review from './steps/Step4Review'
import StepResults from './steps/StepResults'
import { useWizardForm } from './hooks/useWizardForm'
import { WIZARD_STEPS } from './constants/formOptions'

export default function App() {
  return (
    <ThemeProvider>
      <WizardShell />
    </ThemeProvider>
  )
}

function WizardShell() {
  const wizard = useWizardForm()

  return (
    <WizardLayout steps={WIZARD_STEPS.slice(0, 4)} currentStep={Math.min(wizard.step, 4)}>
      {wizard.step === 1 && <Step1Residency form={wizard.form} setField={wizard.setField} onNext={wizard.goNext} />}
      {wizard.step === 2 && (
        <Step2Assets
          form={wizard.form}
          setField={wizard.setField}
          onNext={wizard.goNext}
          onBack={wizard.goBack}
        />
      )}
      {wizard.step === 3 && (
        <Step3Goals form={wizard.form} setField={wizard.setField} onNext={wizard.goNext} onBack={wizard.goBack} />
      )}
      {wizard.step === 4 && (
        <Step4Review
          form={wizard.form}
          onSubmit={wizard.submit}
          onBack={wizard.goBack}
          isSubmitting={wizard.isSubmitting}
          error={wizard.error}
        />
      )}
      {wizard.step === 5 && (
        <StepResults result={wizard.result} onStartOver={() => wizard.goToStep(1)} />
      )}
    </WizardLayout>
  )
}
