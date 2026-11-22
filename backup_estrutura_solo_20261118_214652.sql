CREATE TABLE `TIPO_SOLO` (
  `id_solo` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `nome_solo` varchar(150) COLLATE latin1_general_ci NOT NULL,
  `ordem_solo` varchar(100) COLLATE latin1_general_ci DEFAULT NULL,
  `textura` varchar(100) COLLATE latin1_general_ci DEFAULT NULL,
  `fonte` varchar(255) COLLATE latin1_general_ci DEFAULT NULL,
  `retencao_agua` tinyint(3) unsigned DEFAULT NULL,
  `drenagem` tinyint(3) unsigned DEFAULT NULL,
  `aptidao_graos` tinyint(3) unsigned DEFAULT NULL,
  `profundidade` tinyint(3) unsigned DEFAULT NULL,
  `risco_erosao` tinyint(3) unsigned DEFAULT NULL,
  `culturas_predominantes` varchar(255) COLLATE latin1_general_ci DEFAULT NULL,
  `descricao` text COLLATE latin1_general_ci,
  PRIMARY KEY (`id_solo`),
  UNIQUE KEY `uk_tipo_solo` (`nome_solo`,`ordem_solo`,`textura`)
) ENGINE=InnoDB AUTO_INCREMENT=11 DEFAULT CHARSET=latin1 COLLATE=latin1_general_ci;

CREATE TABLE `CONFIGURACAO_SAFRA` (
  `id_config` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `id_regiao` int(10) unsigned NOT NULL,
  `id_solo` int(10) unsigned NOT NULL,
  `id_cultura` int(10) unsigned NOT NULL,
  `data_plantio` date DEFAULT NULL,
  PRIMARY KEY (`id_config`),
  KEY `idx_config_regiao` (`id_regiao`),
  KEY `idx_config_solo` (`id_solo`),
  KEY `idx_config_cultura` (`id_cultura`),
  CONSTRAINT `fk_config_cultura` FOREIGN KEY (`id_cultura`) REFERENCES `CULTURA` (`id_cultura`) ON UPDATE CASCADE,
  CONSTRAINT `fk_config_regiao` FOREIGN KEY (`id_regiao`) REFERENCES `REGIAO` (`id_regiao`) ON UPDATE CASCADE,
  CONSTRAINT `fk_config_solo` FOREIGN KEY (`id_solo`) REFERENCES `TIPO_SOLO` (`id_solo`) ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=latin1 COLLATE=latin1_general_ci;

