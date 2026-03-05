import type { Metadata } from "next";

import { Providers } from "@/components/Providers";
import { AuthenticatedCopilotKit } from "@/components/AuthenticatedCopilotKit";
import { NoAuthCopilotKit } from "@/components/NoAuthCopilotKit";
import "./globals.css";
import "@copilotkit/react-ui/styles.css";

export const metadata: Metadata = {
  title: "Logistics Assistant",
  description: "Sample application showcasing CopilotKit for logistics data analysis",
  icons: {
    icon: "/favicon.svg",
  },
};

// Check if authentication is enabled via environment variable
const isAuthEnabled = process.env.NEXT_PUBLIC_AUTH_ENABLED === "true";

function CopilotKitWrapper({ children }: { children: React.ReactNode }) {
  if (!isAuthEnabled) {
    return <NoAuthCopilotKit>{children}</NoAuthCopilotKit>;
  }
  return <AuthenticatedCopilotKit>{children}</AuthenticatedCopilotKit>;
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={"antialiased"}>
        <Providers>
          <CopilotKitWrapper>
            {children}
          </CopilotKitWrapper>
        </Providers>
      </body>
    </html>
  );
}
