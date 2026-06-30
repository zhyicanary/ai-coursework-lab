"use client";

import { Inter } from "next/font/google";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Brain, Search, Plane, Settings } from "lucide-react";
import { SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar";
import { AppSidebar } from "@/components/app-sidebar";
import { cn } from "@/lib/utils";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

const navItems = [
    { href: "/", label: "Home", icon: Brain },
    { href: "/knowseeker", label: "KnowSeeker", icon: Search },
    { href: "/tripmind", label: "TripMind", icon: Plane },
    { href: "/settings", label: "Settings", icon: Settings },
];

export default function RootLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    const pathname = usePathname();

    return (
        <html lang="zh-CN" suppressHydrationWarning>
            <body className={inter.className}>
                <SidebarProvider defaultOpen>
                    <AppSidebar />
                    <div className="flex flex-1 flex-col min-h-screen">
                        <header className="sticky top-0 z-40 flex h-14 items-center gap-2 border-b bg-background px-4">
                            <SidebarTrigger className="-ml-1" />
                            <Link
                                href="/"
                                className="flex items-center gap-2 font-semibold"
                            >
                                <Brain className="h-5 w-5 text-primary" />
                                <span>AI Coursework Lab</span>
                            </Link>
                        </header>
                        <main className="flex-1">{children}</main>
                    </div>
                </SidebarProvider>

                {/* Mobile bottom nav (shown only on small screens) */}
                <div className="fixed bottom-0 left-0 right-0 z-50 flex h-14 items-center justify-around border-t bg-background md:hidden">
                    {navItems.map((item) => {
                        const Icon = item.icon;
                        const isActive = pathname === item.href;
                        return (
                            <Link
                                key={item.href}
                                href={item.href}
                                className={cn(
                                    "flex flex-col items-center gap-0.5 px-3 py-1 text-xs transition-colors",
                                    isActive
                                        ? "text-primary"
                                        : "text-muted-foreground hover:text-foreground",
                                )}
                            >
                                <Icon className="h-5 w-5" />
                                {item.label}
                            </Link>
                        );
                    })}
                </div>
            </body>
        </html>
    );
}
