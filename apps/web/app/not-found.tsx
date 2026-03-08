import Link from "next/link";
import { FileQuestion } from "lucide-react";

export default function NotFound() {
  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center px-4 text-center">
      <FileQuestion className="h-12 w-12 text-neutral-400" />
      <h2 className="mt-4 text-2xl font-bold text-neutral-800">
        Page not found
      </h2>
      <p className="mt-2 text-sm text-neutral-500">
        The page you&apos;re looking for doesn&apos;t exist or has been moved.
      </p>
      <Link
        href="/"
        className="mt-6 inline-flex h-10 items-center rounded-md bg-primary-600 px-5 text-sm font-semibold text-white transition-colors hover:bg-primary-700"
      >
        Go home
      </Link>
    </div>
  );
}
