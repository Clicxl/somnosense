import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { useParams } from 'react-router'

export default function MorningReport() {
  const { id } = useParams()
  return (
    <Card>
      <CardHeader>
        <CardTitle>{`Sleep Session ${id}`}</CardTitle>
      </CardHeader>
      <CardContent>The Morning Report will appear here.</CardContent>
    </Card>
  )
}
