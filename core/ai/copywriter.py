import re
from typing import Dict, List, Optional

class AICopywriter:
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.api_key = api_key
        self.base_url = base_url

    def generate_social_pack(
        self,
        transcript: str,
        mode: str = "gaming",
        hook_title: str = ""
    ) -> Dict[str, str]:
        """
        Generates high-converting viral title, social media caption, and hashtags
        ready to copy-paste for TikTok, Reels, and YouTube Shorts.
        """
        words = transcript.strip().split() if transcript else []
        preview = " ".join(words[:15]) + ("..." if len(words) > 15 else "")

        mode_tags = {
            "gaming": ["#gaming", "#gamer", "#gamingshorts", "#clutch", "#streamer", "#fyp", "#viralshorts"],
            "podcast": ["#podcast", "#deepconversation", "#interview", "#mindset", "#quotes", "#fyp", "#trending"],
            "talking_head": ["#tips", "#edukasi", "#faktamenarik", "#creator", "#insight", "#fyp", "#viral"]
        }
        tags = mode_tags.get(mode, ["#shorts", "#fyp", "#viral"])

        # Smart title selection
        title = hook_title if hook_title else "Momen Paling Gila Hari Ini! 🔥"
        if transcript and len(words) >= 4:
            clean_first = re.sub(r'[^\w\s]', '', preview).strip().capitalize()
            if mode == "gaming":
                title = f"{hook_title or 'GOKIL!'} - {clean_first}"
            elif mode == "podcast":
                title = f"Dengerin ini: \"{preview}\" 🎙️"
            else:
                title = f"FAKTA: {clean_first} 💡"

        # Social caption template
        if mode == "gaming":
            caption = (
                f"{title}\n\n"
                f"Asli ga nyangka momen ini bakal kejadian pas lagi main! 😱 "
                f"Kalian pernah ngalamin hal yang sama ga? Tulis di komentar ya! 👇\n\n"
                f"{' '.join(tags)}"
            )
        elif mode == "podcast":
            caption = (
                f"\"{preview}\"\n\n"
                f"Setuju ga sama poin ini? Kadang hal-hal kayak gini baru kita sadari setelah denger perspektif lain. 🎙️\n\n"
                f"Simpan video ini buat reminder kalian! 📌\n\n"
                f"{' '.join(tags)}"
            )
        else:
            caption = (
                f"{title}\n\n"
                f"Banyak yang belum tahu soal ini! Share ke temen kamu yang butuh tahu info ini ya. 🔥\n\n"
                f"{' '.join(tags)}"
            )

        return {
            "title": title,
            "caption": caption,
            "hashtags": " ".join(tags),
            "transcript_summary": preview
        }
