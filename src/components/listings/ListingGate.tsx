import { useDirectory } from "../../context/DirectoryContext";
import { OutbidDialog } from "./OutbidDialog";

type Props = {
  open: boolean;
  onClose: () => void;
};

export function ListingGate({ open, onClose }: Props) {
  const { projects, outbid } = useDirectory();
  const topBid = (projects[0]?.bidUsd ?? 17005) + 1;
  return (
    <OutbidDialog
      open={open}
      defaultAmount={topBid}
      onClose={onClose}
      onSubmit={(input) => {
        outbid(input);
        onClose();
      }}
    />
  );
}
