import PptDemoScreen from '../../components/PptDemoScreen'

export default function PhotoInputScreen() {
  return (
    <PptDemoScreen
      eyebrow="PHOTO SCAN"
      title="Audit a cart from a photo"
      description="Scan an existing basket or shopping list to identify missing quantities, accessories, and delivery risks."
      icon="camera-outline"
      actionLabel="Open camera"
    />
  )
}
