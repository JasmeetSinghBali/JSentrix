import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { MaskContainer } from "@/components/ui/svg-mask-effect";
import { ColourfulText } from "@/components/ui/colourful-text";
import { motion } from "motion/react";
import previewApp from '../../../../nuances/Screenshot_2025-08-01_default_dark_theme.png'
import { Separator } from "@/components/ui/separator";

export function LoginForm({
  className,
  ...props
}: React.ComponentProps<"div">) {
  return (
    <div className="flex h-[40rem] w-full items-center justify-center overflow-hidden">
      <div className="h-screen w-full flex items-center justify-center relative overflow-hidden bg-black">
        <motion.img
            // 🎈 shud be giphy demo preview instead of the running stream in default a2a mode
            src={previewApp}
            className="h-full w-full object-contain absolute inset-0 [mask-image:radial-gradient(circle,transparent,black_80%)] pointer-events-none"
            initial={{ opacity: 0 }}
            animate={{ opacity: 0.5 }}
            transition={{ duration: 1 }}
        />
            <h1 className="text-md md:text-xl lg:text-4xl font-bold text-center text-white relative z-2 font-sans">
                <ColourfulText text="JSentrix @v1.0.0" />
            </h1>
       </div>
      <Separator orientation="vertical" />
      <MaskContainer
        revealText={
            <p className="mx-auto max-w-4xl text-center text-md md:text-xl lg:text-4xl font-bold text-white-800">
                <br/> (AGS) Agentic <span className="text-blue-500">Graph</span> System <br/>
                <br/> private, local and <span className="text-blue-500">multi-agentic</span>  <br/>
                <Separator className="w-80 my-4" /> 
                <span className="text-blue-500">mcp</span> and <span className="text-blue-500">a2a</span> compliant
            </p>
        }
        className="min-h-[30rem] max-h-[40vh] text-white dark:text-black p-4 w-full max-w-4xl mx-auto"
      >
        <div className={cn("flex gap-6 max-w-lg mx-auto", className)} {...props}>
            <Card className="w-full max-w-md mx-auto p-8">
                <CardHeader>
                <CardTitle>Login</CardTitle>
                <CardDescription>
                    Login to your account
                </CardDescription>
                </CardHeader>
                <CardContent>
                <form>
                    <div className="flex flex-col gap-6">
                        <div className="grid gap-3">
                            <Label htmlFor="email">Email</Label>
                            <Input
                            id="email"
                            type="email"
                            placeholder="m@example.com"
                            required
                            />
                        </div>
                    <div className="grid gap-3">
                        <div className="flex items-center">
                        <Label htmlFor="password">Password</Label>
                        {/* <a
                            href="#"
                            className="ml-auto inline-block text-sm underline-offset-4 hover:underline"
                        >
                            Forgot your password?
                        </a> */}
                        </div>
                        <Input id="password" type="password" required />
                    </div>
                    <div className="flex flex-col gap-3">
                        <Button type="submit" className="w-full">
                        Login
                        </Button>
                    </div>
                    </div>
                </form>
                </CardContent>
            </Card>
        </div>
      </MaskContainer>
    </div>
  )
}
