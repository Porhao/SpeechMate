import { LinkButton, PageHeader } from "@/components/ui/kit";

export default function NotFound() {
  return (
    <div className="px-4 sm:px-6 py-16 max-w-[640px] mx-auto">
      <PageHeader eyebrow="404" title="There's nothing at this address.">
        The link may be old, or the session it pointed to was deleted.
      </PageHeader>
      <LinkButton href="/home">Back to home</LinkButton>
    </div>
  );
}
