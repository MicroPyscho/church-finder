import { useNavigate } from "react-router-dom";
import { Check } from "lucide-react";

export default function ConfirmPage() {
  const navigate = useNavigate();
  return (
    <div className="confirm-page">
      <div style={{maxWidth:420,textAlign:"center"}}>
        <div className="confirm-icon"><Check size={22} strokeWidth={2.5}/></div>
        <h1 className="confirm-title">You're in</h1>
        <p style={{fontSize:"0.88rem",color:"var(--mid)",lineHeight:1.65,marginBottom:32,maxWidth:360,margin:"0 auto 32px"}}>
          Check your email to verify your account. Once confirmed, your alerts go live and we'll notify you the moment a matching property appears.
        </p>
        <button className="btn btn-black" onClick={()=>navigate("/")}>Start searching</button>
      </div>
    </div>
  );
}
