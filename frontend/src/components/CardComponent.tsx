import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
function CardComponent() {
  return (
    <Card className="w-full max-w-sm mt-10">
      <CardHeader>
        <CardTitle>Title</CardTitle>
        <CardDescription>
          Description
        </CardDescription>
      </CardHeader>
      <CardContent>
        <p>Content</p>
      </CardContent>
      <CardFooter className="flex-col gap-2">
        <h1>Footer</h1>
      </CardFooter>
    </Card>
  );
}

export default CardComponent;
