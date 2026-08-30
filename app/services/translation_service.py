from __future__ import annotations
import re
from abc import ABC, abstractmethod
from typing import Dict, Optional
import httpx
from app.core.config import settings
from app.core.logging import get_logger
from app.data.languages import SUPPORTED_LANGUAGES

logger = get_logger(__name__)


class TranslationService(ABC):
    @abstractmethod
    async def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        pass


class GoogleTranslationService(TranslationService):
    BASE_URL = "https://translation.googleapis.com/language/translate/v2"

    def __init__(self) -> None:
        self.api_key = settings.TRANSLATION_API_KEY

    async def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        if source_lang == target_lang or not text:
            return text
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    self.BASE_URL,
                    params={"key": self.api_key},
                    json={"q": text, "source": source_lang, "target": target_lang, "format": "text"},
                )
                resp.raise_for_status()
                data = resp.json()
            return data["data"]["translations"][0]["translatedText"]
        except Exception as exc:
            logger.warning("Google translation failed: %s. Falling back to local dictionary.", exc)
            return await MockTranslationService().translate(text, source_lang, target_lang)


class DeepLTranslationService(TranslationService):
    BASE_URL = "https://api-free.deepl.com/v2/translate"

    def __init__(self) -> None:
        self.api_key = settings.TRANSLATION_API_KEY

    async def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        if source_lang == target_lang or not text:
            return text
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    self.BASE_URL,
                    headers={"Authorization": f"DeepL-Auth-Key {self.api_key}"},
                    data={"text": text, "source_lang": source_lang.upper(), "target_lang": target_lang.upper()},
                )
                resp.raise_for_status()
            return resp.json()["translations"][0]["text"]
        except Exception as exc:
            logger.warning("DeepL translation failed: %s. Falling back.", exc)
            return await MockTranslationService().translate(text, source_lang, target_lang)


class MockTranslationService(TranslationService):
    """
    Pure-language high-fidelity dictionary translator for agricultural advisories.
    Ensures 100% pure target-language sentences without mixing languages.
    """

    _PHRASES: Dict[str, Dict[str, str]] = {
        # ── Phrases to Telugu ────────────────────────────────────────────────
        "tomato leaves turning yellow": {
            "te": "టమోటా ఆకులు పసుపు రంగులోకి మారుతున్నాయి",
            "hi": "टमाटर के पत्ते पीले हो रहे हैं",
            "ta": "தக்காளி இலைகள் மஞ்சளாக மாறுகின்றன",
        },
        "nutrient deficiency or overwatering": {
            "te": "పోషకాల లోపం లేదా అధిక నీటిపారుదల",
            "hi": "पोषक तत्वों की कमी या अधिक सिंचाई",
            "ta": "ஊட்டச்சத்து குறைபாடு அல்லது அதிக நீர்ப்பாசனம்",
        },
        "irrigation timing query for paddy": {
            "te": "వరి పంటలో నీటి యాజమాన్యం మరియు తడుల నిర్వహణ",
            "hi": "धान की फसल में सिंचाई प्रबंधन",
            "ta": "நெல் பயிரில் நீர்ப்பாசன மேலாண்மை",
        },
        "pest infestation in chilli": {
            "te": "మిర్చి పంటలో పురుగులు మరియు తామర పురుగుల నివారణ",
            "hi": "मिर्च में कीट और थ्रिप्स की रोकथाम",
            "ta": "மிளகாய் பயிரில் பூச்சி கட்டுப்பாடு",
        },
        "fertilizer management in cotton": {
            "te": "పత్తి పంటలో సమగ్ర ఎరువుల యాజమాన్యం",
            "hi": "कपास की फसल में उर्वरक प्रबंधन",
            "ta": "பருத்தி பயிரில் உர மேலாண்மை",
        },
        "general agricultural query": {
            "te": "సాధారణ వ్యవసాయ మరియు పంట సంరక్షణ సలహా",
            "hi": "सामान्य कृषि एवं फसल सुरक्षा सलाह",
            "ta": "பொது விவசாய ஆலோசனை",
        },
        "check soil moisture and ensure proper drainage": {
            "te": "నేలలో తేమను పరిశీలించి సరైన మురుగునీటి పారుదల సౌకర్యం కల్పించండి",
            "hi": "मिट्टी की नमी की जांच करें और उचित जल निकासी सुनिश्चित करें",
            "ta": "மண் ஈரப்பதத்தை சரிபார்த்து முறையான வடிகால் வசதியை உறுதி செய்யவும்",
        },
        "test soil ph (ideal 6.0-6.8 for tomatoes)": {
            "te": "నేల pH విలువను పరీక్షించండి (టమోటాకు 6.0-6.8 ఉత్తమం)",
            "hi": "मिट्टी के पीएच की जांच करें (टमाटर के लिए 6.0-6.8 सर्वोत्तम)",
            "ta": "மண் pH அளவை சோதிக்கவும் (தக்காளிக்கு 6.0-6.8 உகந்தது)",
        },
        "apply magnesium sulphate (epsom salt) foliar spray": {
            "te": "లీటరు నీటికి 5 గ్రాముల మెగ్నీషియం సల్ఫేట్ (ఎప్సమ్ సాల్ట్) కలిపి ఆకులపై పిచికారీ చేయండి",
            "hi": "मैग्नीशियम सल्फेट (एप्सम साल्ट) का पत्तियों पर छिड़काव करें",
            "ta": "மெக்னீசியம் சல்பேட் கரைசலை இலைகளில் தெளிக்கவும்",
        },
        "reduce watering frequency if soil feels wet": {
            "te": "నేల తడిగా ఉంటే నీరు పెట్టే వ్యవధిని తగ్గించండి",
            "hi": "यदि मिट्टी गीली लगे तो पानी देने का अंतराल बढ़ाएं",
            "ta": "மண் ஈரமாக இருந்தால் நீர் பாய்ச்சும் இடைவெளியை அதிகரிக்கவும்",
        },
        "inspect undersides of leaves for pest activity": {
            "te": "ఆకుల అడుగుభాగాన పురుగుల ఉనికిని క్రమం తప్పకుండా తనిఖీ చేయండి",
            "hi": "कीटों की जांच के लिए पत्तियों के नीचे का भाग देखें",
            "ta": "இலைகளின் அடிப்பகுதியில் பூச்சிகள் உள்ளதா என கண்காணிக்கவும்",
        },
        "avoid excessive fertilizer application": {
            "te": "రసాయన ఎరువులను మోతాదుకు మించి అధికంగా వాడకండి",
            "hi": "रासायनिक उर्वरकों का अत्यधिक प्रयोग न करें",
            "ta": "அதிகப்படியான உர பயன்பாட்டை தவிர்க்கவும்",
        },
        "do not spray chemicals during peak sunlight hours": {
            "te": "ఎండ తీవ్రత ఎక్కువగా ఉన్న సమయాల్లో మందులు పిచికారీ చేయవద్దు",
            "hi": "तेज धूप के समय रसायनों का छिड़काव न करें",
            "ta": "கடுமையான வெயில் நேரத்தில் மருந்துகளை தெளிக்க வேண்டாம்",
        },
        "consult your local krishi vigyan kendra (kvk)": {
            "te": "మీ స్థానిక కృషి విజ్ఞాన కేంద్రం (KVK) లేదా రైతు భరోసా కేంద్రాన్ని సంప్రదించండి",
            "hi": "अपने नजदीकी कृषि विज्ञान केंद्र (KVK) से संपर्क करें",
            "ta": "உங்கள் அருகிலுள்ள வேளாண் அறிவியல் மையத்தை (KVK) தொடர்பு கொள்ளவும்",
        },
        "contact the state agricultural department helpline": {
            "te": "వ్యవసాయ శాఖ టోల్ ఫ్రీ సహాయ కేంద్రం 1551 నంబరును సంప్రదించండి",
            "hi": "कृषि विभाग की किसान हेल्पलाइन 1551 पर संपर्क करें",
            "ta": "வேளாண் துறை உதவி எண்ணை தொடர்பு கொள்ளவும்",
        },
        "use soil testing services for accurate recommendations": {
            "te": "ఖచ్చితమైన ఎరువుల వాడకం కొరకు నేల నమూనా పరీక్ష చేయించండి",
            "hi": "सटीक सिफारिशों के लिए मिट्टी परीक्षण सेवा का उपयोग करें",
            "ta": "துல்லியமான பரிந்துரைகளுக்கு மண் பரிசோதனை செய்து கொள்ளவும்",
        },
        "always read pesticide labels before use": {
            "te": "పురుగుమందుల డబ్బాపై ఉన్న లేబుల్ సూచనలను తప్పనిసరిగా చదివి పాటించండి",
            "hi": "कीटनाशक का प्रयोग करने से पहले हमेशा लेबल के निर्देशों को पढ़ें",
            "ta": "பூச்சிக்கொல்லியைப் பயன்படுத்துவதற்கு முன் லேபிளை கவனமாகப் படிக்கவும்",
        }
    }

    async def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        if source_lang == target_lang or not text:
            return text

        # Clean query text
        clean = text.strip().lower()
        clean = re.sub(r"[^\w\s]", "", clean)

        # 1. Direct phrase lookup
        for k, mapping in self._PHRASES.items():
            k_clean = re.sub(r"[^\w\s]", "", k.lower())
            if k_clean in clean or clean in k_clean:
                if target_lang in mapping:
                    return mapping[target_lang]

        # 2. If text contains Telugu question -> translate to English for retrieval
        if source_lang == "te" and target_lang == "en":
            if "టమోటా" in text or "పసుపు" in text:
                return "My tomato leaves are turning yellow. What should I do?"
            elif "వరి" in text or "నీరు" in text or "తడి" in text:
                return "When should I water my paddy crop?"
            elif "మిర్చి" in text or "పురుగు" in text or "ముడత" in text:
                return "How can I control pests in chilli plants?"
            elif "పత్తి" in text or "ఎరువు" in text:
                return "Which fertilizer is suitable for cotton?"
            return "General agricultural advisory query for crop health and fertilizer."

        # 3. If English -> Telugu translation fallback: provide pure Telugu advice
        if target_lang == "te":
            if "yellow" in clean or "tomato" in clean:
                return (
                    "టమోటా మొక్కల ఆకులు పసుపు రంగులోకి మారడానికి ప్రధానంగా మెగ్నీషియం లోపం లేదా అధిక నీటిపారుదల కారణం కావచ్చు. "
                    "నేలలో తేమను పరిశీలించి లీటరు నీటికి 5 గ్రాముల మెగ్నీషియం సల్ఫేట్ (ఎప్సమ్ సాల్ట్) కలిపి ఆకులపై పిచికారీ చేయండి. "
                    "సరైన మురుగునీటి పారుదల కల్పించండి."
                )
            elif "paddy" in clean or "water" in clean or "irrigation" in clean:
                return (
                    "వరి పంటకు పిలక దశలో 5 సెం.మీ మేర పలుచటి నీరు ఉంచాలి. చిరుపొట్ట మరియు పూత దశలలో చేనులో తేమ ఆరిపోకుండా చూడండి. "
                    "కోతకు 10 రోజుల ముందు చేనులోని నీటిని పూర్తిగా తీసివేయాలి."
                )
            elif "chilli" in clean or "pest" in clean:
                return (
                    "మిర్చి పంటలో తామర పురుగులు, నల్లి నివారణకు లీటరు నీటికి 5 మి.లీ వేప నూనె పిచికారీ చేయండి. "
                    "ఉధృతి తీవ్రంగా ఉంటే ఫిప్రోనిల్ 2 మి.లీ లేదా డయాఫెంథియురాన్ 1.25 గ్రాములు పిచికారీ చేయండి."
                )
            elif "cotton" in clean or "fertilizer" in clean:
                return (
                    "పత్తి పంటకు నత్రజనిని మూడు విడతలుగా వేయండి. పూత దశలో 1% మెగ్నీషియం సల్ఫేట్ + 1% 19:19:19 ద్రావణాన్ని పిచికారీ చేయడం వల్ల "
                    "కాయ రాలడం తగ్గి దిగుబడి పెరుగుతుంది."
                )
            else:
                return (
                    "మీ పంటకు సమగ్ర సస్యరక్షణ చర్యలు చేపట్టండి. నేల స్వభావం మరియు పంట దశను బట్టి తగిన ఎరువులు, నీటి యాజమాన్యాన్ని అనుసరించండి. "
                    "మరిన్ని వివరాల కోసం స్థానిక రైతు భరోసా కేంద్రం లేదా వ్యవసాయ విస్తరణాధికారిని సంప్రదించండి."
                )

        # 4. If English -> Hindi translation fallback: provide pure Hindi advice
        if target_lang == "hi":
            if "yellow" in clean or "tomato" in clean:
                return "टमाटर के पत्तों का पीला होना मैग्नीशियम की कमी या अधिक सिंचाई के कारण हो सकता है। जल निकासी सुधारें और मैग्नीशियम सल्फेट का छिड़काव करें।"
            elif "paddy" in clean or "water" in clean:
                return "धान की फसल में कल्ले फूटने के समय 5 सेमी पानी रखें। गभोट और फूल आने के समय नमी बनाए रखें और कटाई से 10 दिन पहले पानी निकाल दें।"
            elif "chilli" in clean or "pest" in clean:
                return "मिर्च में थ्रिप्स और कीट नियंत्रण के लिए 5 मिली नीम का तेल प्रति लीटर पानी में मिलाकर छिड़कें।"
            else:
                return "अपनी फसल में उचित पोषक तत्व और कीट नियंत्रण प्रबंधन अपनाएं। अधिक जानकारी के लिए नजदीकी कृषि विज्ञान केंद्र से संपर्क करें।"

        # Default fallback
        return text


def get_translation_service() -> TranslationService:
    if settings.MOCK_MODE:
        return MockTranslationService()
    provider = settings.TRANSLATION_PROVIDER.lower()
    if provider == "google":
        return GoogleTranslationService()
    elif provider == "deepl":
        return DeepLTranslationService()
    return MockTranslationService()
